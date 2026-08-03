package com.example.wb.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 扫描 output 文件夹下所有以 w_ 开头的 .json 文件，
 * 解析每个 JSON 内 variants 数组，扁平化为商品列表。
 *
 * 规则：
 * 1. 文件名必须以 w_ 开头、以 .json 结尾
 * 2. JSON 顶层或 data/payload 字段中包含 variants 数组
 * 3. 已上架（hit 含店铺名）的 variant 会被跳过（精确到单个 variant）
 * 4. Ozon 平铺格式（无 variants 字段）按顶层 hit 跳过
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OutputScannerService {

    /** output 文件夹绝对路径，必须在 application.yml 中通过 output.dir 配置 */
    @Value("${output.dir}")
    private String outputDir;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 文件最后修改时间缓存：用于发现新文件 */
    private final Map<String, Long> fileModCache = new ConcurrentHashMap<>();

    @PostConstruct
    public void init() {
        File dir = new File(outputDir);
        if (!dir.exists()) {
            boolean ok = dir.mkdirs();
            log.info("📁 创建 output 文件夹：{}（{}）", dir.getAbsolutePath(), ok ? "成功" : "失败");
        } else {
            log.info("📁 output 文件夹已存在：{}", dir.getAbsolutePath());
        }
    }

    public String getOutputDir() {
        return new File(outputDir).getAbsolutePath();
    }

    /**
     * 无过滤版本：返回所有商品（供 list 接口）
     */
    public List<ProductItem> scanAll() {
        return scanAll(null);
    }

    /**
     * 扫描并过滤商品
     * @param shopName 若非空，则排除 hit 列表中已包含该店铺名的商品
     */
    public List<ProductItem> scanAll(String shopName) {
        File dir = new File(outputDir);
        if (!dir.exists() || !dir.isDirectory()) {
            return Collections.emptyList();
        }
        File[] files = dir.listFiles((f) -> f.isFile()
                && f.getName().toLowerCase().startsWith("w_")
                && f.getName().toLowerCase().endsWith(".json"));
        if (files == null || files.length == 0) {
            return Collections.emptyList();
        }
        Arrays.sort(files, Comparator.comparing(File::getName));

        List<ProductItem> all = new ArrayList<>();
        for (File file : files) {
            try {
                all.addAll(parseFile(file));
            } catch (Exception e) {
                log.error("❌ 解析文件失败：{} - {}", file.getName(), e.getMessage());
            }
        }
        // 按店铺过滤：排除 hit 列表中已包含当前店铺名的商品
        if (shopName != null && !shopName.isBlank()) {
            final String sn = shopName;
            all = all.stream()
                    .filter(item -> item.hit == null || !item.hit.contains(sn))
                    .collect(java.util.stream.Collectors.toList());
        }
        return all;
    }

    public int detectChanges() {
        File dir = new File(outputDir);
        if (!dir.exists() || !dir.isDirectory()) {
            return 0;
        }
        File[] files = dir.listFiles((f) -> f.isFile()
                && f.getName().toLowerCase().startsWith("w_")
                && f.getName().toLowerCase().endsWith(".json"));
        if (files == null) return 0;
        int changed = 0;
        Set<String> currentFiles = new HashSet<>();
        for (File f : files) {
            String name = f.getName();
            currentFiles.add(name);
            long mtime = f.lastModified();
            Long prev = fileModCache.get(name);
            if (prev == null || prev != mtime) {
                fileModCache.put(name, mtime);
                if (prev != null) {
                    changed++;
                    log.info("📝 检测到文件变更：{}", name);
                } else {
                    changed++;
                    log.info("🆕 检测到新文件：{}", name);
                }
            }
        }
        fileModCache.keySet().retainAll(currentFiles);
        return changed;
    }

    /**
     * 解析单个 JSON 文件，提取所有商品
     */
    private List<ProductItem> parseFile(File file) throws IOException {
        JsonNode root = objectMapper.readTree(file);
        JsonNode listNode = extractListNode(root);

        List<ProductItem> items = new ArrayList<>();
        if (listNode == null || !listNode.isArray()) {
            return items;
        }

        for (int i = 0; i < listNode.size(); i++) {
            JsonNode entry = listNode.get(i);

            // WB payload 格式：{ subjectID, variants: [...] }
            if (entry.has("variants") && entry.get("variants").isArray()) {
                JsonNode variants = entry.get("variants");
                int subjectID = entry.has("subjectID") ? entry.get("subjectID").asInt() :
                        (entry.has("subjectId") ? entry.get("subjectId").asInt() : 0);

                for (int vi = 0; vi < variants.size(); vi++) {
                    JsonNode v = variants.get(vi);

                    ProductItem item = new ProductItem();
                    item.sourceFile = file.getName();
                    item.sourceRef = file.getName() + "#" + i + "." + vi;
                    item.entryIndex = i;
                    item.variantIndex = vi;
                    item.subjectID = subjectID;
                    item.vendorCode = textOr(v, "vendorCode", "");
                    item.title = textOr(v, "title", "");
                    item.description = textOr(v, "description", "");
                    item.brand = textOr(v, "brand", "");
                    item.imageUrl = textOr(v, "imageUrl", "");
                    item.price = v.has("price") ? v.get("price").asDouble() : 0;

                    JsonNode skusNode = v.get("skus");
                    if (skusNode != null && skusNode.isArray()) {
                        item.skus = new ArrayList<>();
                        for (JsonNode s : skusNode) item.skus.add(s.asText());
                    } else {
                        item.skus = new ArrayList<>();
                    }

                    if (entry.has("weight")) item.weight = entry.get("weight").asText();
                    if (entry.has("weightKG")) item.weightKG = entry.get("weightKG").asDouble();
                    if (entry.has("dimension")) item.dimension = entry.get("dimension").asText();
                    if (entry.has("sales")) item.sales = entry.get("sales").asText();
                    item.dimensions = parseDimensions(item.dimension, item.weightKG, item.weight);
                    if (entry.has("fulfillment") && entry.get("fulfillment").isArray()) {
                        List<String> ff = new ArrayList<>();
                        entry.get("fulfillment").forEach(n -> ff.add(n.asText()));
                        item.fulfillment = ff;
                    }
                    if (entry.has("crawledImages") && entry.get("crawledImages").isArray()) {
                        List<String> ci = new ArrayList<>();
                        entry.get("crawledImages").forEach(n -> ci.add(n.asText()));
                        item.crawledImages = ci;
                    }
                    // 读取 hit 字段（WB variants 格式）
                    if (v.has("hit")) {
                        JsonNode h = v.get("hit");
                        if (h.isArray()) {
                            item.hit = new ArrayList<>();
                            h.forEach(n -> item.hit.add(n.asText()));
                        }
                    }

                    items.add(item);
                }
            } else {
                // Ozon 平铺格式：{ sku, title, brandName, price, imageUrl, ... }

                ProductItem item = new ProductItem();
                item.sourceFile = file.getName();
                item.sourceRef = file.getName() + "#" + i;
                item.entryIndex = i;
                item.variantIndex = -1;
                item.subjectID = entry.has("wbId") ? entry.get("wbId").asInt() :
                        (entry.has("wbID") ? entry.get("wbID").asInt() : 0);
                item.vendorCode = textOr(entry, "sku", "");
                item.title = textOr(entry, "title", "");
                item.description = textOr(entry, "crawledDescription", textOr(entry, "description", ""));
                item.brand = "";
                item.imageUrl = textOr(entry, "imageUrl", "");
                item.price = entry.has("price") ? entry.get("price").asDouble() : 0;
                item.weight = entry.has("weight") ? entry.get("weight").asText() : null;
                if (entry.has("weightKG")) item.weightKG = entry.get("weightKG").asDouble();
                item.dimension = entry.has("dimension") ? entry.get("dimension").asText() : null;
                item.sales = entry.has("sales") ? entry.get("sales").asText() : null;
                item.dimensions = parseDimensions(item.dimension, item.weightKG, item.weight);
                if (entry.has("fulfillment") && entry.get("fulfillment").isArray()) {
                    List<String> ff = new ArrayList<>();
                    entry.get("fulfillment").forEach(n -> ff.add(n.asText()));
                    item.fulfillment = ff;
                }
                if (entry.has("crawledImages") && entry.get("crawledImages").isArray()) {
                    List<String> ci = new ArrayList<>();
                    entry.get("crawledImages").forEach(n -> ci.add(n.asText()));
                    item.crawledImages = ci;
                }
                if (entry.has("sku")) {
                    item.skus = List.of(entry.get("sku").asText());
                } else {
                    item.skus = new ArrayList<>();
                }
                // 读取 hit 字段（Ozon 平铺格式）
                if (entry.has("hit")) {
                    JsonNode h = entry.get("hit");
                    if (h.isArray()) {
                        item.hit = new ArrayList<>();
                        h.forEach(n -> item.hit.add(n.asText()));
                    }
                }
                items.add(item);
            }
        }
        return items;
    }

    private JsonNode extractListNode(JsonNode root) {
        if (root == null) return null;
        if (root.isArray()) return root;
        if (root.has("data") && root.get("data").isArray()) return root.get("data");
        if (root.has("payload") && root.get("payload").isArray()) return root.get("payload");
        return null;
    }

    private String textOr(JsonNode node, String field, String def) {
        if (node == null || !node.has(field) || node.get(field).isNull()) return def;
        return node.get(field).asText(def);
    }

    /**
     * 给指定 sourceRef 的 hit 列表中添加店铺名（新增行为：仅追加，不影响其他店铺）
     * sourceRef 格式：fileName#entryIndex 或 fileName#entryIndex.variantIndex
     * @param shopName 店铺名称
     */
    public boolean markHit(String sourceRef, String shopName) {
        if (sourceRef == null || !sourceRef.contains("#")) {
            log.warn("⚠️ 标记失败：sourceRef 格式错误 - {}", sourceRef);
            return false;
        }
        if (shopName == null || shopName.isBlank()) {
            log.warn("⚠️ 标记失败：shopName 不能为空");
            return false;
        }
        int hashIdx = sourceRef.lastIndexOf('#');
        String fileName = sourceRef.substring(0, hashIdx);
        String idxPart = sourceRef.substring(hashIdx + 1);

        int entryIndex;
        int variantIndex = -1;
        try {
            if (idxPart.contains(".")) {
                String[] parts = idxPart.split("\\.");
                entryIndex = Integer.parseInt(parts[0]);
                variantIndex = Integer.parseInt(parts[1]);
            } else {
                entryIndex = Integer.parseInt(idxPart);
            }
        } catch (NumberFormatException e) {
            log.warn("⚠️ 标记失败：索引解析错误 - {}", sourceRef);
            return false;
        }

        File file = new File(outputDir, fileName);
        if (!file.exists()) {
            log.warn("⚠️ 标记失败：文件不存在 - {}", fileName);
            return false;
        }
        try {
            JsonNode root = objectMapper.readTree(file);
            JsonNode listNode = extractListNode(root);
            if (listNode == null || !listNode.isArray() || entryIndex >= listNode.size()) {
                log.warn("⚠️ 标记失败：索引越界或结构错误 - sourceRef={}", sourceRef);
                return false;
            }

            ArrayNode arr = (ArrayNode) listNode;
            JsonNode target = arr.get(entryIndex);
            ObjectNode hitNode;

            if (variantIndex >= 0 && target.has("variants") && target.get("variants").isArray()) {
                ArrayNode vars = (ArrayNode) target.get("variants");
                if (variantIndex >= vars.size()) {
                    log.warn("⚠️ 标记失败：variant 索引越界 - sourceRef={}", sourceRef);
                    return false;
                }
                hitNode = (ObjectNode) vars.get(variantIndex);
            } else {
                // Ozon 平铺格式：直接给顶层加 hit
                hitNode = (ObjectNode) target;
            }

            // hit 字段转为 ArrayList<String>，追加店铺名（去重）
            JsonNode hitField = hitNode.get("hit");
            List<String> hitList;
            if (hitField == null) {
                hitList = new ArrayList<>();
                hitNode.set("hit", objectMapper.createArrayNode());
                hitField = hitNode.get("hit");
            } else if (hitField.isArray()) {
                hitList = new ArrayList<>();
                hitField.forEach(n -> hitList.add(n.asText()));
                // 替换为干净的 ArrayList 以便后续操作
                ((ArrayNode) hitField).removeAll();
                for (String s : hitList) ((ArrayNode) hitField).add(s);
            } else {
                // 兼容旧数据 hit=1：迁移为数组
                int oldVal = hitField.asInt();
                hitList = new ArrayList<>();
                if (oldVal == 1) hitList.add("default");
                hitNode.putArray("hit");
                for (String s : hitList) ((ArrayNode) hitNode.get("hit")).add(s);
            }

            if (!hitList.contains(shopName)) {
                ((ArrayNode) hitNode.get("hit")).add(shopName);
            }

            objectMapper.writerWithDefaultPrettyPrinter().writeValue(file, root);
            log.info("✅ 已标记 hit += [{}]：sourceRef={}", shopName, sourceRef);
            fileModCache.remove(fileName);
            return true;
        } catch (Exception e) {
            log.error("❌ 标记 hit 失败：sourceRef={}, err={}", sourceRef, e.getMessage());
            return false;
        }
    }

    @lombok.Data
    public static class ProductItem {
        public String sourceFile;       // 来源 JSON 文件名
        public String sourceRef;        // 唯一引用：fileName#entryIndex[.variantIndex]
        public int entryIndex;
        public int variantIndex = -1;
        public int subjectID;
        public String vendorCode;
        public String title;
        public String description;
        public String brand;
        public List<String> skus;
        public String imageUrl;
        public double price;
        public String weight;
        public Double weightKG;          // 重量（公斤）
        public String dimension;         // 原始字符串 "650×490×440"
        public Map<String, Object> dimensions; // 解析后：{ length, width, height, weightBrutto }
        public String sales;
        public List<String> fulfillment;
        public List<String> crawledImages;
        public List<String> hit;         // 已上架的店铺名列表，null 表示未上架任何店铺
    }

    /**
     * 把 "650×490×440" 这类 dimension 字符串 + weightKG/weight 解析成 WB API 需要的 dimensions 对象。
     * 输入数据单位：mm（爬虫原始数据是 mm）
     * 提交到 WB API 时需要：cm（WB 接口要求 cm，范围 1~700）
     * 重量单位：kg（weightBrutto 也是 kg）
     * 维度分隔符：× / x / X / * / 空格/制表 均可
     *
     * 重量推断规则（按优先级）：
     *   1) weightKG 已经是 kg，直接用
     *   2) weight 是数字：按经验阈值判断单位
     *      - > 5000 → 视为克（>= 5kg 一般会以克存储）
     *      - 其他（<= 5000）→ 视为 kg
     *      注意：低于 500 的小数（如 0.395）应当直接当 kg；但爬虫返回的原始 weight 通常是整数克，
     *      所以加一道 "> 50" 的克阈值判断：
     *      - > 50 且含小数部分 → 视为 kg（原始就是 kg，如 12.5）
     *      - > 50 且为整数 → 视为克（如 395, 16300）
     */
    private static Map<String, Object> parseDimensions(String dimension, Double weightKG, String weight) {
        Map<String, Object> out = new LinkedHashMap<>();
        if (dimension != null && !dimension.isBlank()) {
            String[] parts = dimension.trim().split("[×xX*\\s]+");
            try {
                if (parts.length >= 1) out.put("length", mmToCm(Integer.parseInt(parts[0].trim())));
                if (parts.length >= 2) out.put("width",  mmToCm(Integer.parseInt(parts[1].trim())));
                if (parts.length >= 3) out.put("height", mmToCm(Integer.parseInt(parts[2].trim())));
            } catch (NumberFormatException ignored) {}
        }
        Double wKg = weightKG;
        if (wKg == null && weight != null && !weight.isBlank()) {
            try {
                double raw = Double.parseDouble(weight.trim());
                wKg = guessKgFromRaw(raw);
            } catch (NumberFormatException ignored) {}
        }
        if (wKg != null && wKg > 0) out.put("weightBrutto", roundKg(wKg));
        return out.isEmpty() ? null : out;
    }

    /**
     * 根据经验阈值把 raw 值推断成 kg。
     * - raw > 5000 一律视为克（5kg 以上的整数一般是克）
     * - raw > 50 但 <= 5000：原始是整数且绝对值 > 50 → 视为克（如 395, 16300）；
     *                     原始是 kg 直接用（如 12.5）
     * - raw <= 50：视为 kg（kg 一般不会超过 50 用于电商家用）
     */
    private static double guessKgFromRaw(double raw) {
        if (raw > 5000) return raw / 1000.0;
        // 介于 50 ~ 5000：判断小数位
        if (raw > 50) {
            // 如果是整数（如 395.0、16300.0）→ 克；如果是小数（如 12.5）→ kg
            return (raw == Math.floor(raw)) ? raw / 1000.0 : raw;
        }
        // <= 50：视为 kg
        return raw;
    }

    private static double roundKg(double v) {
        return Math.round(v * 1000) / 1000.0;
    }

    /** 毫米 → 厘米，四舍五入到整数（WB API 接收整数 cm）。最小返回 1 避免被接口拒。 */
    private static int mmToCm(int mm) {
        int cm = (int) Math.round(mm / 10.0);
        return Math.max(cm, 1);
    }
}