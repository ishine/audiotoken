"""
This script tests the batched implementation of the encodec model and compares it with the original implementation based on SI SNR.
"""

import torch
from time import time
from pathlib import Path
from queue import Queue
from matplotlib import pyplot as plt
from torchmetrics.audio import ScaleInvariantSignalNoiseRatio

from src.encoder import VoiceEncoder
from src.decoder import VoiceDecoder
from src.utils import process_audio
from src.configs import VoiceEncoderConfig, VoiceDecoderConfig

if __name__ == '__main__':

    audio_file_paths = ['~/Desktop/meraki/encodec/test_24k.wav']
    audio_files: Queue[torch.Tensor] = Queue()
    audio_file = process_audio(
        Path(audio_file_paths[0]).expanduser(),
        VoiceEncoderConfig.model_sample_rate
    )
    audio_files.put(audio_file)

    voice_encoder = VoiceEncoder(
        bandwidth=VoiceEncoderConfig.bandwidth,
        single_segment_duration=VoiceEncoderConfig.single_segment_duration,
        batch_size=VoiceEncoderConfig.batch_size,
        overlap=VoiceEncoderConfig.overlap,
    )

    voice_decoder = VoiceDecoder(
        bandwidth=VoiceDecoderConfig.bandwidth,
        single_segment_duration=VoiceDecoderConfig.single_segment_duration,
        overlap=VoiceDecoderConfig.overlap,
    )

    si_snr = ScaleInvariantSignalNoiseRatio()

    ### ----------------- Original implementation ----------------- ###

    start_time = time()
    with torch.no_grad():
        out = voice_encoder.model(audio_file.unsqueeze(0))

    print(f'[Original implementation] Complete process took {time() - start_time:.2f}s and SI SNR: {si_snr(out[0], audio_file)}')

    ### ----------------- Batched implementation ----------------- ###

    start_time = time()
    encoded_audio = voice_encoder(read_q=audio_files)

    encoded_result: Queue[torch.Tensor] = Queue()
    for idx, batch in enumerate(encoded_audio):
        encoded_result.put(batch)

    decoded_audio = voice_decoder(read_q=encoded_result)

    out_batched = []
    for idx, batch in enumerate(decoded_audio):
        out_batched.append(batch)

    print(f'[Batched implementation] Complete process took {time() - start_time:.2f}s and SI SNR: {si_snr(out_batched[0][:480000], audio_file[0])}')

    plt.figure()
    plt.plot(audio_file[0], label='Original Audio')
    plt.plot(out[0][0], label='Single Pass Output')
    plt.plot(out_batched[0][:480000], label='Batched Output')
    plt.legend()
    plt.show()