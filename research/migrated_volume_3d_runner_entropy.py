#!/usr/bin/env python3
import migrated_volume_3d_codec as codec
import migrated_volume_3d_entropy as entropy
codec.pack=entropy.pack
codec.unpack=entropy.unpack
import migrated_volume_3d_runner as runner
if __name__=='__main__':
 entropy.sanity()
 runner.main()
