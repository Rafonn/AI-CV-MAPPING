# app/services/llm_service.py

from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM
import torch
from typing import Optional, List, Dict, Any

try:
    summarizer_model_name = "philschmid/bart-large-cnn-samsum"
    summarizer_tokenizer = AutoTokenizer.from_pretrained(summarizer_model_name)
    summarizer_model = AutoModelForSeq2SeqLM.from_pretrained(summarizer_model_name)
    summarizer = pipeline("summarization", model=summarizer_model, tokenizer=summarizer_tokenizer)

    matcher_model_name = "google/gemma-2b-it"
    print(f"Carregando tokenizer para o modelo de matching: {matcher_model_name}")
    matcher_tokenizer = AutoTokenizer.from_pretrained(matcher_model_name)
    
    print(f"Carregando modelo de matching: {matcher_model_name}. Isso pode levar algum tempo e consumir RAM...")

    try:
        if torch.cuda.is_available():
            print("GPU detectada. Tentando carregar modelo em float16 para otimizar VRAM.")
            matcher_model = AutoModelForCausalLM.from_pretrained(matcher_model_name, torch_dtype=torch.float16, device_map="auto")
        else:
            print("Nenhuma GPU detectada ou torch não configurado para CUDA. Carregando modelo em CPU (pode ser lento para Gemma-2b-it).")
            matcher_model = AutoModelForCausalLM.from_pretrained(matcher_model_name, torch_dtype=torch.bfloat16)
    except Exception as model_load_exc:
        print(f"Falha ao carregar modelo com otimizações: {model_load_exc}. Tentando carregamento padrão.")
        matcher_model = AutoModelForCausalLM.from_pretrained(matcher_model_name)

    if matcher_tokenizer.pad_token_id is None:
        print(f"Definindo pad_token_id como eos_token_id ({matcher_tokenizer.eos_token_id}) para o tokenizer de matching.")
        matcher_tokenizer.pad_token_id = matcher_tokenizer.eos_token_id
    
    text_generator = pipeline(
        "text-generation",
        model=matcher_model,
        tokenizer=matcher_tokenizer,
        max_new_tokens=400,
    )
    print(f"Modelo de matching {matcher_model_name} carregado e pipeline criado.")

except Exception as e:
    print(f"Erro CRÍTICO ao carregar modelos LLM: {e}. Funcionalidade de LLM pode estar comprometida.")
    summarizer = None
    text_generator = None

def generate_summary(text: str, max_length: int = 150, min_length: int = 30) -> str:
    if not summarizer or not text.strip():
        return "Não foi possível gerar o sumário (modelo de sumarização não carregado ou texto vazio)."
    try:
        max_input_length = summarizer.tokenizer.model_max_length - 20
        inputs = summarizer.tokenizer(text, max_length=max_input_length, truncation=True, return_tensors="pt")

        summary_ids = summarizer.model.generate(
            inputs["input_ids"],
            num_beams=4,
            max_length=max_length + 20,
            min_length=min_length,
            early_stopping=True
        )
        summary_text = summarizer.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary_text
    except Exception as e:
        print(f"Erro na sumarização LLM: {e}")
        return f"Erro ao gerar sumário: {e}"

def find_best_match(query_jd: str, resume_data: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    if not text_generator:
        return {"file_name": "Erro de Configuração", "justification": "O modelo LLM para matching não foi carregado corretamente."}
    if not resume_data:
        return {"file_name": "Nenhum Currículo", "justification": "Nenhum currículo fornecido para análise."}

    # --- Prompt Aprimorado ---
    context = f"Analise os seguintes currículos em relação aos REQUISITOS DA VAGA abaixo.\n\n"
    context += f"PERGUNTA: {query_jd}\n\n"
    context += "CURRÍCULOS PARA ANÁLISE:\n"

    for i, resume in enumerate(resume_data):
        context += f"--- CURRÍCULO {i+1} (Arquivo: {resume['file_name']}) ---\n"
        resume_text_preview = (resume['text'][:1500] + '...') if len(resume['text']) > 1500 else resume['text']
        context += f"{resume_text_preview}\n\n"
    
    prompt_instructions = (
        "Tarefa:\n"
        "1. Identifique qual dos currículos acima é o MAIS adequado com a pergunta. Pode ser mais de um\n"
        "2. Forneça uma justificativa CLARA e DETALHADA para sua escolha, baseada especificamente no conteúdo dos currículos e como ele se alinha a PERGUNTA DO USUARIO.\n"
        "RESPONDA APENAS COM O(S) NOME(S) DO(S) ARQUIVO(S) E A SUA JUSTIFICATIVA\n\n"
    )
    full_prompt = context + prompt_instructions

    placeholder_justificativa_template = "[Escreva aqui a SUA ANÁLISE DETALHADA. Seja conciso mas completo. Não repita o texto do currículo, mas sim explique sua conclusão.]"

    #print(f"DEBUG: Prompt para Gemma (primeiros 500 chars):\n{full_prompt[:500]}\n...\n--------------------")

    try:
        """ generated_outputs = text_generator(
            full_prompt,
            temperature=0.1, # Temperatura muito baixa para respostas mais certas e menos criativas
            do_sample=True, # Precisa ser True para temperature ter efeito
        ) """

        input_text = full_prompt
        input_ids = matcher_tokenizer(input_text, return_tensors="pt")

        generated_outputs = matcher_model.generate(**input_ids)
        
        raw_llm_response_with_prompt = matcher_tokenizer.decode(generated_outputs[0])

        print(raw_llm_response_with_prompt)
        
        #print(raw_llm_response_with_prompt)
        llm_generated_part = "vazio"
        if raw_llm_response_with_prompt.startswith(full_prompt):
             llm_generated_part = raw_llm_response_with_prompt[len(full_prompt):].strip()
        else:
            model_turn_start = "<start_of_turn>model\n"
            if model_turn_start in raw_llm_response_with_prompt:
                llm_generated_part = raw_llm_response_with_prompt.split(model_turn_start, 1)[-1].strip()
            else:
                 llm_generated_part = raw_llm_response_with_prompt # Fallback
            print(f"AVISO: O prompt não foi encontrado no início da resposta completa do LLM, ou a resposta não continha '{model_turn_start}'. Usando heurística ou resposta completa para extração.")

        print(f"\n\n\nDEBUG: Resposta isolada do LLM (Gemma):\n{llm_generated_part}\n--------------------")

        chosen_file = None
        justification = "O LLM não forneceu uma resposta no formato esperado."

        if "ARQUIVO:" in llm_generated_part and "JUSTIFICATIVA:" in llm_generated_part:
            try:
                file_part_text = llm_generated_part.split("ARQUIVO:", 1)[1].split("JUSTIFICATIVA:", 1)[0].strip()
                just_part_text = llm_generated_part.split("JUSTIFICATIVA:", 1)[1].strip()

                for resume in resume_data:
                    if file_part_text and (file_part_text.lower() in resume['file_name'].lower() or resume['file_name'].lower() in file_part_text.lower()):
                        chosen_file = resume['file_name']
                        break
                
                if not chosen_file and file_part_text:
                    print(f"AVISO: LLM mencionou '{file_part_text}' como arquivo, mas não correspondeu a nenhum arquivo enviado.")
                    chosen_file = f"Nome de arquivo não reconhecido ({file_part_text})"

                if not just_part_text or just_part_text == placeholder_justificativa_template or just_part_text.startswith(placeholder_justificativa_template):
                    justification = "O LLM não forneceu uma justificativa específica ou apenas repetiu o template do prompt."
                    print(f"AVISO: LLM não forneceu justificativa válida. Parte da justificativa original: '{just_part_text}'")
                elif placeholder_justificativa_template in just_part_text:
                    cleaned_justification = just_part_text.replace(placeholder_justificativa_template, "").strip()
                    justification = cleaned_justification if cleaned_justification else "O LLM incluiu o template na justificativa, sem análise adicional clara."
                    print(f"AVISO: LLM incluiu placeholder na justificativa. Limpa: '{justification}'")
                else:
                    justification = just_part_text

            except IndexError:
                justification = f"Formato da resposta do LLM parcialmente reconhecido, mas falha ao dividir ARQUIVO/JUSTIFICATIVA. Resposta: {llm_generated_part}"
                print(f"ERRO DE PARSING (IndexError): {llm_generated_part}")
            except Exception as e:
                justification = f"Erro inesperado ao parsear resposta do LLM: {str(e)}. Resposta: {llm_generated_part}"
                print(f"ERRO DE PARSING (Inesperado - {str(e)}): {llm_generated_part}")
        else:
            justification = f"LLM não seguiu o formato ARQUIVO/JUSTIFICATIVA. Resposta gerada: {llm_generated_part if llm_generated_part else '(vazia)'}"
            print(f"AVISO: LLM não usou keywords ARQUIVO/JUSTIFICATIVA. Resposta gerada: {llm_generated_part}")
            if not chosen_file and resume_data:
                 chosen_file = "Análise Geral (ver justificativa)"
        
        if chosen_file:
            return {"file_name": chosen_file, "justification": justification}
        elif llm_generated_part:
             return {"file_name": "Nenhum arquivo específico destacado pelo LLM", "justification": justification}
        else:
            return {"file_name": "Nenhum candidato destacado pelo LLM", "justification": "O LLM não forneceu uma resposta clara ou ocorreu um erro."}

    except Exception as e:
        print(f"Erro CRÍTICO na inferência do LLM para matching: {e}")
        return {"file_name": "Erro no processamento LLM", "justification": f"Exceção durante a análise pelo LLM: {str(e)}"}