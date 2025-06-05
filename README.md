# Sistema Inteligente de Triagem de Currículos (CV-AI)

## Visão Geral

O CV-AI é uma aplicação inteligente projetada para auxiliar recrutadores e gestores de contratação a otimizar o processo de triagem de currículos. A ferramenta automatiza a extração de informações de currículos em formato PDF ou imagem, gera sumários concisos e é capaz de classificar os candidatos com base em requisitos específicos de uma vaga, fornecendo justificativas. Adicionalmente, todas as interações são registradas para fins de auditoria e análise.

Com o CV-AI, o usuário poderá dedicar mais tempo a entrevistas e estratégias de contratação, em vez de tarefas manuais e repetitivas.

## Funcionalidades Principais

1.  **Upload Múltiplo:** Aceita múltiplos arquivos de currículo nos formatos PDF, JPEG e PNG.
2.  **Extração de Texto (OCR):** Utiliza tecnologia OCR para extrair o texto de currículos baseados em imagem.
3.  **Sumarização Automática:** Gera sumários claros e objetivos para cada currículo processado.
4.  **Matching Inteligente com Vagas:** Responde a perguntas como "Qual desses currículos se enquadra melhor para a vaga de Engenheiro de Software com requisitos {...}?" com justificativas baseadas no conteúdo dos currículos.
5.  **Logging Detalhado:** Registra cada requisição em um banco de dados não relacional (MongoDB), incluindo `request_id`, `user_id`, `timestamp`, `query` e o `resultado`, sem armazenar o conteúdo completo dos arquivos para otimizar custos e privacidade.

## Tech Stack

* **Linguagem:** Python 3.9+
* **Framework API:** FastAPI
* **Servidor ASGI:** Uvicorn
* **Bibliotecas OCR:** EasyOCR (com PyMuPDF para PDFs e Pillow para imagens)
* **Bibliotecas LLM:** Hugging Face Transformers (para modelos open-source)
* **Banco de Dados:** MongoDB (Não Relacional)
* **Conteinerização:** Docker

## IMPORTANTE

Com docker, a aplicação é mais lenta pois ele opera dentro de limites de recursos (principalmente RAM) que podem ser mais restritos do que quando você roda o script Python diretamente na sua máquina.
Para resolver, crie ou edite o arquivo .wslconfig na sua pasta de usuário: C:\Users\<SeuNomeDeUsuario>\.wslconfig:

```bash
  [wsl2]
  memory=5GB   # Exemplo para um sistema com 8GB (para 16bgb, recomendo usar "10GB")
  processors=4 # Ajuste para o número de processadores que você quer alocar
  # swap=2GB     # Pode ajudar a evitar que o processo morra, mas deixa tudo lento
```

## Pré-requisitos

Antes de começar, garanta que você tem os seguintes softwares instalados:

* Python 3.9 ou superior
* Pip (gerenciador de pacotes Python)
* Docker e Docker Compose (opcional, para rodar com `docker-compose`)
* Acesso a uma instância MongoDB (local ou na nuvem, como MongoDB Atlas)
* Uma conta no [Hugging Face](https://huggingface.co/) (necessária para baixar alguns modelos LLM)

## Configuração do Projeto

1.  **Clone o Repositório (se aplicável):**
    ```bash
    # git clone <url_do_seu_repositorio>
    # cd <nome_do_repositorio>
    ```

2.  **Crie e Ative um Ambiente Virtual Python:**
    É altamente recomendado usar um ambiente virtual.
    ```bash
    python -m venv venv
    # No Windows:
    .\venv\Scripts\activate
    # No macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Instale as Dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Autenticação no Hugging Face (Necessário para modelos como Gemma):**
    * Acesse a página dos modelos que exigem aceite de termos (ex: `google/gemma-2b-it`) no Hugging Face Hub e aceite os termos.
    * No seu terminal (com o ambiente virtual ativo), logue-se no Hugging Face:
        ```bash
        huggingface-cli login
        ```
        Você precisará de um token de acesso da sua conta Hugging Face (Configurações -> Access Tokens).

5.  **Configure as Variáveis de Ambiente:**
    Crie um arquivo chamado `.env` na raiz do projeto com as seguintes variáveis (substitua pelos seus valores):
    ```env
    MONGODB_URL="mongodb://localhost:27017/" # Ou sua string de conexão do MongoDB Atlas
    MONGODB_DATABASE_NAME="cv_ai_db"
    HUGGING_FACE_HUB_TOKEN="hf_SEU_TOKEN_AQUI" # Opcional se 'huggingface-cli login' foi usado e suficiente
    ```
    A aplicação carregará essas variáveis automaticamente. O `HUGGING_FACE_HUB_TOKEN` aqui é especialmente útil se você for rodar via Docker e quiser que o container se autentique, ou se o `huggingface-cli login` não estiver funcionando no seu ambiente por algum motivo.

## Executando a Aplicação

### 1. Localmente com Uvicorn (para Desenvolvimento)

* Certifique-se de que seu ambiente virtual está ativo e as dependências instaladas.
* Garanta que sua instância MongoDB está acessível.
* Execute o servidor Uvicorn:
    ```bash
    uvicorn app.main:app --reload
    ```
    * `--reload`: O servidor reiniciará automaticamente após alterações no código.

* Acesse a API em `http://localhost:8000`.
* A documentação interativa (Swagger UI) estará disponível em `http://localhost:8000/docs`.

### 2. Com Docker

1.  **Construa a Imagem Docker:**
    No diretório raiz do projeto (onde está o `Dockerfile`), execute:
    ```bash
    docker build -t cv-ai-app .
    ```

2.  **Execute o Container Docker:**
    ```bash
    docker run -d -p 8001:8000 \
      -e MONGODB_URL="mongodb://seu_host_mongo:27017/cv_ai_db" \
      -e MONGODB_DATABASE_NAME="cv_ai_db" \
      -e HUGGING_FACE_HUB_TOKEN="hf_SEU_TOKEN_AQUI" \
      --name cv-ai-container \
      cv-ai-app
    ```
    * `-d`: Roda em modo detached (segundo plano).
    * `-p 8001:8000`: Mapeia a porta 8001 do seu computador para a porta 8000 do container. Você acessará em `http://localhost:8001`.
    * `-e MONGODB_URL=...`: **Importante:** Se seu MongoDB estiver rodando no host e você estiver no Linux, `localhost` não funcionará. Use o IP da interface Docker (ex: `172.17.0.1`) ou configure uma network Docker. Se estiver usando Docker Desktop for Windows/Mac, `host.docker.internal` pode ser usado no lugar de `localhost` na string de conexão (ex: `mongodb://host.docker.internal:27017/`). Se o MongoDB também estiver em um container Docker, use o nome do serviço do MongoDB na string de conexão e conecte ambos a uma mesma rede Docker.
    * `-e HUGGING_FACE_HUB_TOKEN=...`: Necessário para baixar modelos "gated" (como Gemma) de dentro do container, se ainda não estiverem cacheados na imagem.
    * `--name cv-ai-container`: Nomeia o container.
    * `cv-ai-app`: Nome da imagem construída.

    **Observação sobre cache de modelos no Docker:** Para persistir os modelos baixados entre reinicializações de containers, considere usar um volume Docker para o diretório de cache do Hugging Face (`/root/.cache/huggingface`).

## Como usar?

Após rodar a aplicação, abra a aba "Currículos", clique em "Try it out" e preencha os campos.
Para mais de um currículo, clique em "add string item" e adicione quantos curríclos forem necessários.

**IMPORTANTE:** Quanto mais currículos forem analisados, maior será o processamento da máquina em que a aplicação está rodando.

## Uso da API

A API possui um endpoint principal para processamento de currículos.

### `POST /process-resumes`

* **Descrição:** Recebe arquivos de currículo, um ID de requisição, ID de usuário e, opcionalmente, uma query (descrição da vaga). Retorna sumários ou o melhor candidato.
* **Acesso à Documentação Interativa:** `http://localhost:8000/docs` (ou a porta que você mapeou no Docker).
* **Request Body:** `multipart/form-data`
    * `request_id`: `string` (UUID ou similar, obrigatório)
    * `user_id`: `string` (Identificador do solicitante, obrigatório)
    * `query`: `string` (Opcional. Descrição da vaga e requisitos. Se não informado, retorna sumários individuais)
    * `files`: `List[UploadFile]` (Lista de arquivos PDF, JPG/PNG, obrigatório)

* **Exemplo de Requisição (`curl`):**

    * **Para Sumarização:**
        ```bash
        curl -X POST "http://localhost:8000/process-resumes" \
          -H "accept: application/json" \
          -H "Content-Type: multipart/form-data" \
          -F "request_id=sumario-$(uuidgen)" \
          -F "user_id=fabio_teste" \
          -F "files=@/caminho/para/curriculo1.pdf" \
          -F "files=@/caminho/para/curriculo2.png"
        ```

    * **Para Matching com Vaga:**
        ```bash
        curl -X POST "http://localhost:8000/process-resumes" \
          -H "accept: application/json" \
          -H "Content-Type: multipart/form-data" \
          -F "request_id=match-$(uuidgen)" \
          -F "user_id=fabio_teste" \
          -F "query=Engenheiro de Software Sênior com experiência em Python, FastAPI e microsserviços." \
          -F "files=@/caminho/para/curriculo_dev_senior.pdf" \
          -F "files=@/caminho/para/curriculo_dev_junior.pdf"
        ```

## Estrutura do Log no MongoDB

Os logs são armazenados na coleção `usage_logs` (ou o nome definido em `MONGODB_DATABASE_NAME`) com a seguinte estrutura:

```json
{
  "_id": "ObjectId(...)", // Gerado pelo MongoDB
  "request_id": "string",
  "user_id": "string",
  "timestamp": "ISODate(...)", // Data e hora da requisição
  "query": "string | null",   // A query da vaga, se fornecida
  "result": { /* Conteúdo da resposta JSON enviada ao usuário */ },
  "error": "string | null"    // Mensagem de erro, se alguma falha ocorreu no processamento
}
