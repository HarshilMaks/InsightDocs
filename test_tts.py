import pyttsx3
try:
    engine = pyttsx3.init()
    print("pyttsx3 initialized successfully")
    engine.save_to_file('Hello World', 'test.wav')
    engine.runAndWait()
    print("Audio generated successfully")
except Exception as e:
    print(f"pyttsx3 failed: {e}")
