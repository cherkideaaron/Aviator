import tensorflow as tf
import os

model_path = r'c:\Users\Rescue\Desktop\Cool Project\Aviator\BettingAgent\Models\LSTM\lstm_bit_predictor.keras'
with open('model_info.txt', 'w') as f:
    if os.path.exists(model_path):
        try:
            model = tf.keras.models.load_model(model_path)
            f.write(f"Model loaded successfully.\n")
            f.write(f"Input shape: {model.input_shape}\n")
            f.write(f"Output shape: {model.output_shape}\n")
            # Capture summary
            import io
            stream = io.StringIO()
            model.summary(print_fn=lambda x: stream.write(x + '\n'))
            f.write(stream.getvalue())
        except Exception as e:
            f.write(f"Error loading model: {e}\n")
    else:
        f.write(f"Model not found at {model_path}\n")
