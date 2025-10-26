import sounddevice as sd
import numpy as np
import time

def record_and_check_mic(duration=3, fs=44100):
    """Grava áudio por `duration` segundos e verifica se há sinal."""
    print(f"Gravando por {duration} segundos... Fale no microfone.")
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
        sd.wait()  # Espera a gravação terminar

        # Verifica se há algum sinal significativo (não apenas ruído de fundo)
        peak_amplitude = np.max(np.abs(recording))
        
        print(f"Gravação concluída. Pico de amplitude: {peak_amplitude:.4f}")

        if peak_amplitude > 0.01:  # Um limiar simples para detectar som
            print("SUCESSO: Microfone detectou som.")
            return True
        else:
            print("FALHA: Microfone não detectou som ou o sinal está muito baixo.")
            print("Verifique se o microfone correto está selecionado como padrão e o volume está ajustado.")
            return False
            
    except Exception as e:
        print(f"ERRO ao tentar gravar: {e}")
        print("Possíveis causas:")
        print("- Nenhum dispositivo de entrada de áudio encontrado ou selecionado.")
        print("- O dispositivo pode estar sendo usado por outro aplicativo (desmarque 'controle exclusivo').")
        print("- Driver de áudio corrompido ou ausente.")
        return False

if __name__ == "__main__":
    record_and_check_mic()