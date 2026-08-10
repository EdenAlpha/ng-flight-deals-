#!/usr/bin/env bash
set -euo pipefail
rm -rf work out && mkdir -p work out
git clone -q --depth 1 https://github.com/android/architecture-samples.git work/android-src
rm -rf work/android-src/.git
tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf work/android_app_raw.tar -C work/android-src app build.gradle.kts settings.gradle.kts gradle.properties 2>/dev/null || tar --sort=name --mtime='UTC 2020-01-01' --owner=0 --group=0 -cf work/android_app_raw.tar -C work/android-src app
sha256sum work/android_app_raw.tar | tee out/sha256.txt
stat -c 'original %s' work/android_app_raw.tar | tee out/results.txt
xz -9e -k -f work/android_app_raw.tar; stat -c 'xz9e %s' work/android_app_raw.tar.xz | tee -a out/results.txt
brotli -q 11 -f -o out/android.tar.br work/android_app_raw.tar; stat -c 'brotli11 %s' out/android.tar.br | tee -a out/results.txt
zstd --ultra -22 -q -f work/android_app_raw.tar -o out/android.tar.zst; stat -c 'zstd22 %s' out/android.tar.zst | tee -a out/results.txt
7z a -bd -y -t7z -mx=9 -m0=lzma2 out/android-lzma2.7z work/android_app_raw.tar >/dev/null; stat -c '7z_lzma2 %s' out/android-lzma2.7z | tee -a out/results.txt
7z a -bd -y -t7z -mx=9 -m0=PPMd out/android-ppmd.7z work/android_app_raw.tar >/dev/null; stat -c '7z_ppmd %s' out/android-ppmd.7z | tee -a out/results.txt
# Also test solid compression of the unpacked tree directly rather than pre-TAR byte stream.
7z a -bd -y -t7z -mx=9 -m0=lzma2 out/tree-lzma2.7z work/android-src/app work/android-src/build.gradle.kts work/android-src/settings.gradle.kts work/android-src/gradle.properties >/dev/null; stat -c '7z_tree_lzma2 %s' out/tree-lzma2.7z | tee -a out/results.txt
7z a -bd -y -t7z -mx=9 -m0=PPMd out/tree-ppmd.7z work/android-src/app work/android-src/build.gradle.kts work/android-src/settings.gradle.kts work/android-src/gradle.properties >/dev/null; stat -c '7z_tree_ppmd %s' out/tree-ppmd.7z | tee -a out/results.txt
cat out/results.txt
