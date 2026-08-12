import research.imperial_growing_waveform_language as g

# Identical experiment to PR269, but one representative channel from each
# precommitted cable regime instead of eight. All history checkpoints,
# quantization, phrase length, probabilities, and target remain frozen.
g.W = 1

if __name__ == '__main__':
    g.main()
