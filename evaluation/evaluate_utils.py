from bert_score import score

def compute_avg_sentence_length(sentences):
    if not sentences:
        return 0.0
    word_counts = [len(sentence.split()) for sentence in sentences]
    avg_length = sum(word_counts) / len(word_counts)
    return avg_length

def compute_bertscore(originals, rewrites, model_type='bert-base-multilingual-cased'):
    P, R, F1 = score(cands=rewrites, refs=originals, lang="ko", model_type=model_type, rescale_with_baseline=True)
    return float(F1.mean())

def print_model_report(model_name, f1, avg_len):
    print(f"평가 결과 - {model_name}")
    print(f"──────────────────────────────")
    print(f"KoBERTScore: {f1:.4f}")
    print(f"평균 문장 길이: {avg_len:.2f} 단어")
    print(f"──────────────────────────────")
    
def evaluate_model(originals, rewrites, model_name='MyModel'):
    bertscore = compute_bertscore(originals, rewrites)
    avg_len = compute_avg_sentence_length(rewrites)

    print_model_report(model_name, bertscore, avg_len)