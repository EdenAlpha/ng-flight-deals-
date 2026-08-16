import bz2, json, lzma, math, sys, zlib
import h5py
import numpy as np
import zstandard as zstd

import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar
import imperial_persistent_ar32_full_array_jit as inc

C = 128
NT = 4096
T0 = 14488
TRAIN = 1024
P = 32
STEP = 267
REGIONS = (("hard", 512), ("easy", 2304))
HEADER_BYTES = 64  # shape, transform, serializer, compressor, model reference/version
Z19 = zstd.ZstdCompressor(level=19)
ZD = zstd.ZstdDecompressor()


def signed_dtype(a):
    a = np.asarray(a)
    mn = int(a.min()) if a.size else 0
    mx = int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'), np.dtype('<i2'), np.dtype('<i4')):
        ii = np.iinfo(dt)
        if mn >= ii.min and mx <= ii.max:
            return dt
    return np.dtype('<i8')


def unsigned_dtype(a):
    a = np.asarray(a)
    mx = int(a.max()) if a.size else 0
    for dt in (np.dtype('u1'), np.dtype('<u2'), np.dtype('<u4')):
        if mx <= np.iinfo(dt).max:
            return dt
    return np.dtype('<u8')


def zigzag(a):
    x = np.asarray(a, np.int64)
    return ((x << 1) ^ (x >> 63)).astype(np.uint64)


def unzigzag(u):
    z = np.asarray(u, np.uint64)
    return ((z >> 1).astype(np.int64) ^ -(z & 1).astype(np.int64)).astype(np.int32)


def transforms(K):
    K = np.asarray(K, np.int32)
    yield 'raw_ct', K.copy(), lambda a: np.asarray(a, np.int32)
    yield 'raw_tc', K.T.copy(), lambda a: np.asarray(a, np.int32).T.copy()

    a = K.copy()
    a[:, 1:] = K[:, 1:] - K[:, :-1]
    yield 'delta_time', a, lambda x: np.cumsum(np.asarray(x, np.int32), axis=1, dtype=np.int32)

    a = K.copy()
    a[1:] = K[1:] - K[:-1]
    yield 'delta_channel', a, lambda x: np.cumsum(np.asarray(x, np.int32), axis=0, dtype=np.int32)

    a = K.copy()
    a[0, 1:] = K[0, 1:] - K[0, :-1]
    a[1:, 0] = K[1:, 0] - K[:-1, 0]
    a[1:, 1:] = K[1:, 1:] - K[:-1, 1:] - K[1:, :-1] + K[:-1, :-1]
    yield 'lorenzo2d', a, lambda x: np.cumsum(np.cumsum(np.asarray(x, np.int32), axis=0, dtype=np.int32), axis=1, dtype=np.int32)


def serialize_signed(a):
    a = np.asarray(a)
    dt = signed_dtype(a)
    raw = np.ascontiguousarray(a).astype(dt).tobytes()
    shape = tuple(a.shape)
    def dec(buf):
        return np.frombuffer(buf, dt, count=a.size).astype(np.int32).reshape(shape)
    return 'signed_' + dt.str, raw, dec


def serialize_zigzag(a):
    a = np.asarray(a, np.int32)
    u = zigzag(a)
    dt = unsigned_dtype(u)
    raw = np.ascontiguousarray(u).astype(dt).tobytes()
    shape = tuple(a.shape)
    def dec(buf):
        q = np.frombuffer(buf, dt, count=a.size).astype(np.uint64).reshape(shape)
        return unzigzag(q)
    return 'zigzag_' + dt.str, raw, dec


def serialize_bitplanes(a):
    a = np.asarray(a, np.int32)
    u = zigzag(a).ravel()
    width = max(1, int(int(u.max()).bit_length()) if u.size else 1)
    parts = []
    for b in range(width):
        bits = ((u >> b) & 1).astype(np.uint8)
        parts.append(np.packbits(bits, bitorder='little').tobytes())
    raw = b''.join(parts)
    n = int(u.size)
    plane_bytes = (n + 7) // 8
    shape = tuple(a.shape)
    def dec(buf):
        out = np.zeros(n, np.uint64)
        off = 0
        for b in range(width):
            chunk = np.frombuffer(buf[off:off+plane_bytes], np.uint8)
            bits = np.unpackbits(chunk, bitorder='little')[:n].astype(np.uint64)
            out |= bits << b
            off += plane_bytes
        return unzigzag(out.reshape(shape))
    return 'bitplanes_w%d' % width, raw, dec


def compressors():
    return (
        ('zstd19', lambda b: Z19.compress(b), lambda b: ZD.decompress(b)),
        ('lzma9e', lambda b: lzma.compress(b, format=lzma.FORMAT_XZ, preset=9 | lzma.PRESET_EXTREME), lambda b: lzma.decompress(b, format=lzma.FORMAT_XZ)),
        ('bz2_9', lambda b: bz2.compress(b, compresslevel=9), bz2.decompress),
        ('zlib9', lambda b: zlib.compress(b, 9), zlib.decompress),
    )


def replay_ok(K, cd, X, eps):
    R = inc.decode(np.asarray(K, np.int32), cd)
    me = float(np.max(np.abs(X - R.astype(np.float64))))
    if me > eps * (1 + 1e-12):
        raise RuntimeError(('hard error', me, eps))
    return me


def incumbent(X, eps):
    old = m.STEP
    m.STEP = STEP
    try:
        co = ar.fit_shared(X[:, :TRAIN], P)
        model_bytes, cd = ar.model_frame(co)
        R, K = inc.build(X, cd)
        fr = m.encode_k(K)
        Kd = np.asarray(fr[2], np.int32)
        if not np.array_equal(Kd, K):
            raise RuntimeError('incumbent K decode mismatch')
        Rd = inc.decode(Kd, cd)
        if not np.array_equal(Rd, R):
            raise RuntimeError('incumbent source replay mismatch')
        me = float(np.max(np.abs(X - Rd.astype(np.float64))))
        if me > eps * (1 + 1e-12):
            raise RuntimeError(('incumbent hard error', me, eps))
        return int(model_bytes), cd, np.asarray(K, np.int32), {
            'innovation_bytes': int(fr[0]),
            'model_bytes': int(model_bytes),
            'total_bytes': int(fr[0]) + int(model_bytes) + HEADER_BYTES,
            'rep': fr[1],
            'maxerr': me,
            'k_zero_fraction': float(np.mean(K == 0)),
            'k_std': float(np.std(K)),
        }
    finally:
        m.STEP = old


def audit_address(K, cd, X, eps, model_bytes):
    candidates = []
    serializers = (serialize_signed, serialize_zigzag, serialize_bitplanes)
    for tname, A, inv_transform in transforms(K):
        for sfun in serializers:
            sname, raw, deserialize = sfun(A)
            for cname, enc, dec in compressors():
                blob = enc(raw)
                raw2 = dec(blob)
                if raw2 != raw:
                    raise RuntimeError(('lossless byte mismatch', tname, sname, cname))
                A2 = deserialize(raw2)
                K2 = inv_transform(A2)
                if not np.array_equal(K2, K):
                    raise RuntimeError(('K reconstruction mismatch', tname, sname, cname))
                me = replay_ok(K2, cd, X, eps)
                total = len(blob) + int(model_bytes) + HEADER_BYTES
                candidates.append({
                    'transform': tname,
                    'serializer': sname,
                    'compressor': cname,
                    'payload_bytes': len(blob),
                    'raw_address_bytes': len(raw),
                    'total_bytes': int(total),
                    'bps': 8.0 * total / K.size,
                    'maxerr': me,
                })
    candidates.sort(key=lambda z: z['total_bytes'])
    return candidates


def main(path):
    with h5py.File(path, 'r') as f:
        d = f['Acoustic']
        if tuple(d.shape) != (30000, 6912):
            raise RuntimeError(('shape', d.shape))
        _, std = m.stats(d)
        eps = 0.1 * std
        rows = []
        for region, c0 in REGIONS:
            X = np.asarray(d[T0:T0+NT, c0:c0+C], np.float64).T
            szb, ori = m.szrun(X, eps)
            mb, cd, K, base = incumbent(X, eps)
            cand = audit_address(K, cd, X, eps, mb)
            best = cand[0]
            best['gain_vs_incumbent'] = base['total_bytes'] / best['total_bytes']
            best['gain_vs_sz3'] = int(szb) / best['total_bytes']
            base['bps'] = 8.0 * base['total_bytes'] / K.size
            base['gain_vs_sz3'] = int(szb) / base['total_bytes']
            row = {
                'region': region,
                'c0': c0,
                'shape': [C, NT],
                'samples': int(K.size),
                'global_std': std,
                'eps': eps,
                'sz3': {'bytes': int(szb), 'bps': 8.0 * int(szb) / K.size, 'orientation': ori},
                'incumbent_ar32_step267': base,
                'best_recursive_address': best,
                'top_candidates': cand[:16],
                'candidate_count': len(cand),
            }
            rows.append(row)
            print(json.dumps(row, indent=2), flush=True)
        out = {
            'global_std': std,
            'eps': eps,
            'shape': [C, NT],
            't0': T0,
            'step': STEP,
            'rows': rows,
            'scope': 'Decoder-real self-complexity / recursive-restriction audit of the ACTUAL incumbent AR32 innovation address. The incumbent AR32 source state and K stream are unchanged. Reversible raw/time-major/time-delta/channel-delta/Lorenzo transforms are combined with signed, zigzag, or exact bitplane serialization, then actual Zstd-19, LZMA-extreme, BZip2-9, and zlib-9 streams compete. Every candidate is losslessly decompressed, inverted to the exact original K stream, replayed through the unchanged AR32 decoder, and independently hard-error checked. Model bytes and a fixed 64-byte transform/serializer/compressor header are fully charged. Selection is per object and encoded in that header. No restriction factors, entropy estimates, ideal mass, oracle side information, or target-trained probability model count as compression.',
        }
        with open('imperial_address_self_complexity_audit.json', 'w') as g:
            json.dump(out, g, indent=2)


if __name__ == '__main__':
    main(sys.argv[1])
