# ----------------------------------------
# Requirements (Install before use)
# ----------------------------------------
# !pip install matplotlib scikit-learn
# !pip install bert-score
# !pip install evaluate sacremoses sacrebleu

# Version Info:
# matplotlib==3.10.0  
# scikit-learn==1.6.1  
# bert-score==0.3.13  
# evaluate==0.4.3  
# sacremoses==0.1.1  
# sacrebleu==2.5.1  
# torch==2.6.0  
# transformers==4.52.2  
# pandas==2.2.2  
# numpy==2.0.2  
# tqdm==4.67.1  
# requests==2.32.3  

# ----------------------------------------
# Models and Evaluation Metrics (via Hugging Face)
# ----------------------------------------
# BERTScore: google-bert/bert-base-multilingual-cased
# SARI: evaluate-metric/sari
# ----------------------------------------

from bert_score import score
import evaluate

def compute_avg_sentence_length(sentences):
    if not sentences:
        return 0.0
    word_counts = [len(sentence.split()) for sentence in sentences]
    avg_length = sum(word_counts) / len(word_counts)
    return avg_length

def compute_bertscore(originals, rewrites, model_type='bert-base-multilingual-cased'):
    P, R, F1 = score(cands=rewrites, refs=originals, lang="ko", model_type=model_type, rescale_with_baseline=True)
    return float(F1.mean())

sari_metric = evaluate.load("sari")

def compute_sari(originals, rewrites, references):
    scores = []
    for src, pred, ref in zip(originals, rewrites, references):
        result = sari_metric.compute(
            predictions=[pred],
            references=[[ref]],
            sources=[src]
        )
        scores.append(result['sari'])
    return sum(scores) / len(scores)

def print_originals_and_rewrites(originals, rewrites):
    for i, (ori, rewrite) in enumerate(zip(originals, rewrites)):
        print(f"[{i+1}] Original : {ori}")
        print(f"[{i+1}] Rewrite  : {rewrite}")
        print("-" * 40)


def print_model_report(model_name, f1, avg_len, sari):
    """
    평가 결과를 출력합니다.
    - f1: BERTScore (float)
    - avg_len: 평균 문장 길이 (float)
    - sari: SARI 점수 (float)
    """
    print(f"평가 결과 - {model_name}")
    print(f"──────────────────────────────")
    print(f"KoBERTScore:     {f1:.4f}")
    print(f"SARI Score:      {sari:.2f}")
    print(f"평균 문장 길이:   {avg_len:.2f} 단어")
    print(f"──────────────────────────────")
    
def evaluate_model(originals, rewrites, references, model_name='MyModel'):
    """
    전체 평가 흐름을 통합 실행합니다.
    
    Parameters:
    - originals: 원본 문장 리스트
    - rewrites: 모델이 생성한 문장 리스트
    - references: 정답 문장 리스트 -> `original_text`에 대응되는 `simple_text`를 참조하여 구성해야 함.
    - model_name: 출력 시 모델 이름
    
    Returns:
    - dict: 평가 결과 (BERTScore, SARI, 평균 문장 길이)
    """
    bertscore = compute_bertscore(originals, rewrites)
    avg_len = compute_avg_sentence_length(rewrites)
    sari = compute_sari(originals, rewrites, references)

    print_model_report(model_name, bertscore, avg_len, sari)
    print_originals_and_rewrites(originals, rewrites)