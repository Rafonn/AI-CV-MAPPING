from huggingface_hub import snapshot_download
import os

# --- Modelos para baixar ---
models_to_download = {
    "summarizer": {
        "id": "philschmid/bart-large-cnn-samsum",
        "path": "./manual_models/summarizer_model" # Pasta local para este modelo
    },
    "matcher": {
        "id": "google/gemma-2b-it", # Ou o modelo que você escolheu
        "path": "./manual_models/matcher_model"   # Pasta local para este modelo
    }
}

# --- Token de acesso do Hugging Face (opcional, mas recomendado para modelos privados/gated) ---
# Se você já fez 'huggingface-cli login', geralmente não é necessário passar o token aqui.
# Mas se precisar, pode obter em https://huggingface.co/settings/tokens
# hf_token = "seu_token_aqui" 

def download_model_snapshot(model_id, local_dir, token=None):
    print(f"Iniciando download do modelo: {model_id} para {local_dir}")
    os.makedirs(local_dir, exist_ok=True)
    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False, # Use False para copiar os arquivos diretamente
            # token=token, # Descomente se precisar passar o token explicitamente
            # ignore_patterns=["*.safetensors"], # Exemplo: se quiser apenas arquivos .bin
        )
        print(f"Modelo {model_id} baixado com sucesso em {local_dir}")
    except Exception as e:
        print(f"Erro ao baixar {model_id}: {e}")

if __name__ == "__main__":
    # Crie a pasta principal se não existir
    os.makedirs("./manual_models", exist_ok=True)

    for model_key, model_info in models_to_download.items():
        download_model_snapshot(model_info["id"], model_info["path"])

    print("Downloads manuais concluídos (ou tentados).")