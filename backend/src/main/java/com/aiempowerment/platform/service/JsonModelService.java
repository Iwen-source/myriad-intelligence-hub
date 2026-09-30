package com.aiempowerment.platform.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.util.*;

/**
 * 纯 Java 随机森林推理服务
 * 加载 Python sklearn 导出的 JSON 模型（树结构）
 * 无需 ONNX/PMML native 库，零外部依赖
 */
@Slf4j
@Service
public class JsonModelService {

    private RandomForestModel model;
    private boolean modelLoaded = false;

    @PostConstruct
    public void init() {
        try {
            ObjectMapper mapper = new ObjectMapper();
            try (InputStream is = new ClassPathResource("models/resource_rating_model.json").getInputStream()) {
                model = mapper.readValue(is, RandomForestModel.class);
            }

            log.info("✅ 纯Java模型加载成功: {} 棵树, {} 个特征",
                    model.n_estimators, model.n_features);
            modelLoaded = true;

        } catch (Exception e) {
            log.error("❌ 模型加载失败: {}", e.getMessage(), e);
            modelLoaded = false;
        }
    }

    /**
     * 预测单个资源质量评分 (0.5-5.0)
     */
    public double predict(Map<String, Object> features) {
        if (!modelLoaded) return 3.0;

        try {
            float[] inputArray = buildInputArray(features);
            double sum = 0.0;

            for (TreeNode tree : model.trees) {
                sum += predictTree(tree, inputArray);
            }

            return Math.round((sum / model.n_estimators) * 10.0) / 10.0;
        } catch (Exception e) {
            log.error("模型预测失败: {}", e.getMessage());
            return 3.0;
        }
    }

    /**
     * 递归遍历单棵决策树
     */
    private double predictTree(TreeNode node, float[] features) {
        while (!node.leaf) {
            if (features[node.feature] <= node.threshold) {
                node = node.left;
            } else {
                node = node.right;
            }
        }
        return node.value;
    }

    /**
     * 将资源特征转为模型输入向量
     * 必须与 Python 训练时的 OneHot 顺序完全一致
     */
    private float[] buildInputArray(Map<String, Object> features) {
        float[] arr = new float[model.n_features];
        for (int i = 0; i < model.n_features; i++) {
            String fn = model.feature_names.get(i);
            Object val = features.get(fn);
            if (val instanceof Number n) {
                arr[i] = n.floatValue();
            } else {
                arr[i] = 0f;
            }
        }
        return arr;
    }

    public boolean isModelLoaded() {
        return modelLoaded;
    }

    public List<String> getFeatureNames() {
        return model.feature_names;
    }

    // ========== 内部模型类 ==========

    static class RandomForestModel {
        public int n_estimators;
        public int n_features;
        public List<String> feature_names;
        public List<TreeNode> trees;
    }

    static class TreeNode {
        public int id;
        public int depth;
        public boolean leaf;
        public int feature;
        public String feature_name;
        public double threshold;
        public double value;
        public TreeNode left;
        public TreeNode right;
    }
}
