"""基于 TF-IDF + LSA 的向量记忆检索：触景生情。

记忆文本都很短，且中文没有空格，因此使用字级 n-gram 向量化；
再用 TruncatedSVD 降维到潜在语义空间，最后算余弦相似度。
LSA 能把共现频率高的字词压缩到相近的主题维度上，
从而在无外部模型的前提下获得一点轻量级的语义联想能力。
"""

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class VectorMemory:
    """在有限的历史独白中检索最相似的一条。"""

    MIN_SIMILARITY = 0.5
    RAW_MIN_SIMILARITY = 0.15  # 字面兜底：TF-IDF 余弦低于此值直接判不匹配
    N_COMPONENTS = 100

    def recall(self, query: str, memories: list[str]) -> str | None:
        """返回相似度超过阈值的旧记忆；没有命中则返回 None。"""
        if not query or not memories:
            return None
        vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(memories)
        # 主题数不能超过特征数，也不能超过样本数（10 条记忆最多 9 个主题）
        n_components = min(
            self.N_COMPONENTS, matrix.shape[1] - 1, matrix.shape[0] - 1
        )
        if n_components >= 1:
            # 只在历史记忆上拟合主题空间，查询作为新样本投影进去
            svd = TruncatedSVD(n_components=n_components, random_state=42)
            memory_vectors = svd.fit_transform(matrix)
            query_vector = svd.transform(vectorizer.transform([query]))
        else:
            # 只有一条记忆时无需降维，直接比原空间
            memory_vectors = matrix.toarray()
            query_vector = vectorizer.transform([query]).toarray()
        similarities = cosine_similarity(query_vector, memory_vectors)[0]

        # 字面兜底：LSA 排序结果必须在原始 TF-IDF 空间中也有足够重合。
        # 只统计「连续两字」，避免单字巧合约（"好""我"）把无关句子抬到阈值以上。
        gate = TfidfVectorizer(analyzer="char", ngram_range=(2, 2))
        gate_matrix = gate.fit_transform(memories)
        raw_similarities = cosine_similarity(gate.transform([query]), gate_matrix)[0]
        candidates = np.where(raw_similarities >= self.RAW_MIN_SIMILARITY)[0]
        if len(candidates) == 0:
            return None
        best = int(candidates[np.argmax(similarities[candidates])])
        if similarities[best] > self.MIN_SIMILARITY:
            return memories[best]
        return None

