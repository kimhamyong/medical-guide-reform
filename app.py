# app.py
import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import os

# 경로 설정
DATA_PATH = "./data/combined_dataset.csv"

# 1. 데이터 로드
df = pd.read_csv(DATA_PATH)
originals = df["original_text"].tolist()
simples = df["simple_text"].tolist()

# 2. 모델 로딩 + 인덱스 구축
print("모델과 데이터셋을 로딩 중입니다...")
model = SentenceTransformer("jhgan/ko-sroberta-multitask")
original_embeddings = model.encode(originals, convert_to_numpy=True)
faiss.normalize_L2(original_embeddings)

index = faiss.IndexFlatIP(original_embeddings.shape[1])
index.add(original_embeddings)

# 3. 리트리벌 함수
def retrieve_simple_text(user_input):
    embedding = model.encode([user_input], convert_to_numpy=True)
    faiss.normalize_L2(embedding)
    distances, indices = index.search(embedding, 1)
    return simples[indices[0][0]]

# 4. 사용자 입력 루프
def main():
    print("\n=== 의료 안내문 쉬운 말 리라이팅 시스템 ===\n")
    while True:
        user_input = input("변환할 문장을 입력하세요 (종료: exit): ").strip()
        if user_input.lower() == "exit":
            print("종료합니다.")
            break
        result = retrieve_simple_text(user_input)
        print(f"변경된 문장: {result}\n")

if __name__ == "__main__":
    main()
