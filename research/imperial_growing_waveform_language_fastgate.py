import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import imperial_growing_waveform_language as g

# Identical experiment to PR269, but one representative channel from each
# precommitted cable regime instead of eight. All history checkpoints,
# quantization, phrase length, probabilities, and target remain frozen.
# Parent now defines checkpoints as the immediately preceding 2/8/32/128
# records; this commit retriggers the stacked gate against that correction.
g.W = 1

if __name__ == '__main__':
    g.main()
