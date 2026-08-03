package com.example.wb.service;

import com.example.wb.dto.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class WbApiService {

    private static final String CONTENT_BASE_URL = "https://content-api.wildberries.ru";
    private static final String PRICE_API_URL = "https://discounts-prices-api.wildberries.ru/api/v2/upload/task";
    private static final String MARKETPLACE_BASE_URL = "https://marketplace-api.wildberries.ru";

    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final WbRateLimiter rateLimiter;

    private HttpHeaders createHeaders(String token) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Authorization", token != null && !token.isBlank() ? token : "");
        return headers;
    }

    // ==================== 0. 生成条形码 ====================
    public List<String> generateWbBarcodes(int count) {
        return generateWbBarcodes(count, null);
    }

    public List<String> generateWbBarcodes(int count, String token) {
        String url = CONTENT_BASE_URL + "/content/v2/barcodes";
        BarcodeRequest requestBody = new BarcodeRequest(count);
        HttpEntity<BarcodeRequest> entity = new HttpEntity<>(requestBody, createHeaders(token));

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                ResponseEntity<WbBaseResponse> response = restTemplate.postForEntity(url, entity, WbBaseResponse.class);
                WbBaseResponse resData = response.getBody();

                if (resData != null && Boolean.FALSE.equals(resData.getError())) {
                    @SuppressWarnings("unchecked")
                    List<String> barcodes = (List<String>) resData.getData();
                    log.info("✅ 成功从 WB 官方申请到 {} 个条形码: {}", barcodes.size(), barcodes);
                    return barcodes;
                } else {
                    log.error("❌ 申请条形码失败: {}", resData != null ? resData.getErrorText() : "空响应");
                    return Collections.emptyList();
                }
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 请求条形码接口异常: ", e);
                return Collections.emptyList();
            }
        }
        return Collections.emptyList();
    }

    // ==================== 1. 提交商品卡片 ====================
    public boolean uploadCard(List<ProductUploadPayload> payload) {
        return uploadCard(payload, null);
    }

    public boolean uploadCard(List<ProductUploadPayload> payload, String token) {
        String url = CONTENT_BASE_URL + "/content/v2/cards/upload";
        log.info("🚀 正在提交商品卡片...");
        HttpEntity<List<ProductUploadPayload>> entity = new HttpEntity<>(payload, createHeaders(token));

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                ResponseEntity<WbBaseResponse> response = restTemplate.postForEntity(url, entity, WbBaseResponse.class);
                WbBaseResponse resData = response.getBody();

                if (resData != null && Boolean.FALSE.equals(resData.getError())) {
                    log.info("✅ 卡片上传任务提交成功！(HTTP 200)");
                    return true;
                } else {
                    String formattedJson = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsString(resData);
                    log.error("❌ 提交失败，API 返回完整响应:\n{}", formattedJson);
                    return false;
                }
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 请求异常: ", e);
                return false;
            }
        }
        return false;
    }

    // ==================== 2. 上传商品图片 ====================
    public boolean uploadProductImage(long nmId, int photoOrder, File imageFile) {
        return uploadProductImage(nmId, photoOrder, imageFile, null);
    }

    public boolean uploadProductImage(long nmId, int photoOrder, File imageFile, String token) {
        String url = CONTENT_BASE_URL + "/content/v3/media/file";
        log.info("📸 正在为 nmID [{}] 上传第 {} 张图片: {}", nmId, photoOrder, imageFile.getName());

        if (!imageFile.exists()) {
            log.error("❌ 图片文件不存在: {}", imageFile.getAbsolutePath());
            return false;
        }

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.MULTIPART_FORM_DATA);
                headers.set("Authorization", token != null && !token.isBlank() ? token : "");
                headers.set("X-Nm-Id", String.valueOf(nmId));
                headers.set("X-Photo-Number", String.valueOf(photoOrder));

                MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
                body.add("uploadfile", new org.springframework.core.io.FileSystemResource(imageFile));

                HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

                ResponseEntity<WbBaseResponse> response = restTemplate.postForEntity(url, requestEntity, WbBaseResponse.class);
                WbBaseResponse resData = response.getBody();

                if (resData != null && Boolean.FALSE.equals(resData.getError())) {
                    log.info("✅ 图片上传成功！");
                    return true;
                } else {
                    log.error("❌ 图片上传失败: {}", resData != null ? resData.getErrorText() : "未知错误");
                    return false;
                }
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 上传图片接口调用异常: ", e);
                return false;
            }
        }
        return false;
    }

    // ==================== 2.1 通过 URL 上传商品图片 ====================
    public boolean uploadProductImageByUrls(long nmId, List<String> urls) {
        return uploadProductImageByUrls(nmId, urls, null);
    }

    public boolean uploadProductImageByUrls(long nmId, List<String> urls, String token) {
        String url = CONTENT_BASE_URL + "/content/v3/media/save";
        log.info("🔗 正在为 nmID [{}] 通过 URL 上传 {} 个媒体文件", nmId, urls.size());

        Map<String, Object> body = Map.of(
                "nmId", nmId,
                "data", urls
        );
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, createHeaders(token));

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                ResponseEntity<WbBaseResponse> response = restTemplate.postForEntity(url, entity, WbBaseResponse.class);
                WbBaseResponse resData = response.getBody();

                if (resData != null && Boolean.FALSE.equals(resData.getError())) {
                    log.info("✅ URL 图片上传成功！");
                    return true;
                } else {
                    log.error("❌ URL 图片上传失败: {}", resData != null ? resData.getErrorText() : "未知错误");
                    return false;
                }
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 URL 上传图片接口调用异常: ", e);
                return false;
            }
        }
        return false;
    }

    // ==================== 2.2 设置商品价格 ====================
    public boolean setProductPrices(List<Map<String, Object>> prices, String token) {
        String url = PRICE_API_URL;
        log.info("💰 正在批量设置 {} 个商品价格...", prices.size());

        if (prices == null || prices.isEmpty() || prices.size() > 1000) {
            log.warn("⚠️ 价格数据数量不在 1~1000 范围内");
            return false;
        }
        Map<String, Object> body = Map.of("data", prices);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, createHeaders(token));

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                ResponseEntity<String> response = restTemplate.postForEntity(url, entity, String.class);
                String rawJson = response.getBody();
                log.info("💰 价格设置接口返回：{}", rawJson);
                if (response.getStatusCode().is2xxSuccessful()) {
                    log.info("✅ 价格设置成功！");
                    return true;
                }
                log.error("❌ 价格设置失败: {}", rawJson);
                return false;
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (HttpClientErrorException e) {
                log.error("💥 设置价格失败：HTTP {}，WB 返回：{}", e.getStatusCode(), e.getResponseBodyAsString());
                return false;
            } catch (Exception e) {
                log.error("💥 设置价格接口调用异常: ", e);
                return false;
            }
        }
        return false;
    }

    public List<Object> checkErrorsDetailed(String token) {
        String url = CONTENT_BASE_URL + "/content/v2/cards/error/list?locale=zh";
        Map<String, Object> cursor = new java.util.LinkedHashMap<>();
        cursor.put("limit", 100);
        Map<String, Object> body = Map.of("cursor", cursor, "order", Map.of("ascending", true));
        try {
            ResponseEntity<Map> response = restTemplate.postForEntity(url, new HttpEntity<>(body, createHeaders(token)), Map.class);
            Object data = response.getBody() == null ? null : response.getBody().get("data");
            if (data instanceof Map<?, ?> map && map.get("items") instanceof List<?> items) return new ArrayList<>(items);
            if (data instanceof List<?> items) return new ArrayList<>(items);
            return Collections.emptyList();
        } catch (Exception e) {
            log.error("💥 查询详细上架错误失败: ", e);
            return List.of(e.getMessage());
        }
    }

    // ==================== 3. 检查后台错误 ====================
    public List<Object> checkErrors() {
        return checkErrors(null);
    }

    public List<Object> checkErrors(String token) {
        String url = CONTENT_BASE_URL + "/content/v2/cards/error/list";
        log.info("🔍 正在检查后台异步处理日志...");
        HttpEntity<String> entity = new HttpEntity<>("{}", createHeaders(token));

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                ResponseEntity<WbBaseResponse> response = restTemplate.postForEntity(url, entity, WbBaseResponse.class);
                WbBaseResponse resData = response.getBody();

                if (resData != null && Boolean.TRUE.equals(resData.getError())) {
                    log.error("❌ 查错接口请求失败: {}", resData.getErrorText());
                    return List.of(resData.getErrorText());
                }

                if (resData != null && resData.getData() != null) {
                    Object data = resData.getData();
                    List<Object> errors;
                    if (data instanceof List<?> list) {
                        errors = new ArrayList<>(list);
                    } else if (data instanceof Map<?, ?> map) {
                        errors = List.of(map);
                    } else {
                        errors = List.of(data);
                    }

                    if (errors.isEmpty()) {
                        log.info("🎉 后台无错误日志！");
                        return null;
                    }

                    log.warn("⚠️ 发现 {} 条错误记录/字段警告:", errors.size());
                    for (int i = 0; i < errors.size(); i++) {
                        log.warn("   [{}] 错误详情: {}", i + 1, errors.get(i));
                    }
                    return errors;
                }
                return null;
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 检查错误日志失败: ", e);
                return null;
            }
        }
        return null;
    }

    public synchronized Map<String, Object> getGoodsPrices(List<Long> nmIds, String token) {
        String url = "https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter";
        List<Long> validIds = nmIds == null ? Collections.emptyList() : nmIds.stream()
                .filter(id -> id != null && id > 0)
                .distinct()
                .toList();
        if (validIds.isEmpty()) return Collections.emptyMap();
        final int batchSize = 20;
        List<Object> mergedGoods = new ArrayList<>();
        for (int start = 0; start < validIds.size(); start += batchSize) {
            List<Long> batchList = new ArrayList<>(validIds.subList(start, Math.min(start + batchSize, validIds.size())));
            Map<String, Object> body = Map.of("nmList", batchList);
            try {
                log.info("💰 查询商品价格批次：第 {} 批，{} 个商品", (start / batchSize) + 1, batchList.size());
                rateLimiter.acquire();
                Thread.sleep(1200);
                ResponseEntity<Map> response = restTemplate.postForEntity(url, new HttpEntity<>(body, createHeaders(token)), Map.class);
                Map<String, Object> responseBody = response.getBody();
                if (responseBody == null) continue;
                Object data = responseBody.get("data");
                if (data instanceof Map<?, ?> dataMap && dataMap.get("listGoods") instanceof List<?> goods) {
                    mergedGoods.addAll(goods);
                } else if (data instanceof List<?> goods) {
                    mergedGoods.addAll(goods);
                } else if (responseBody.get("listGoods") instanceof List<?> goods) {
                    mergedGoods.addAll(goods);
                }
            } catch (HttpClientErrorException e) {
                log.error("💥 获取商品价格第 {} 批失败：HTTP {}", (start / batchSize) + 1, e.getStatusCode());
            } catch (Exception e) {
                log.error("💥 获取商品价格第 {} 批失败: ", (start / batchSize) + 1, e);
            }
        }
        Map<String, Object> merged = new java.util.LinkedHashMap<>();
        merged.put("data", Map.of("listGoods", mergedGoods));
        log.info("✅ 商品价格查询完成：请求 {} 个，返回 {} 个", validIds.size(), mergedGoods.size());
        return merged;
    }

    // ==================== 4. 获取当前商家全部商品列表 ====================
    public List<CardListResponse.Card> getAllCards() {
        return getAllCards(null);
    }

    public List<CardListResponse.Card> getAllCards(String token) {
        String url = CONTENT_BASE_URL + "/content/v2/get/cards/list";
        // 关键：limit 拉到 1000 减少分页次数，避免新货号因排序位置落到后几页被过滤
        int limit = 1000;
        String updatedAt = null;
        Long nmID = null;
        List<CardListResponse.Card> allCards = new java.util.ArrayList<>();
        java.util.Set<Long> seenNmIds = new java.util.HashSet<>();
        int emptyStreak = 0; // 连续空页次数，连续 N 次为空就停止翻页
        int noProgressStreak = 0; // 本页没有新增任何 nmID 的次数
        Long prevNmId = null;
        String prevUpdatedAt = null;

        log.info("📦 正在分页拉取当前商家全部商品列表...");
        while (true) {
            CardListRequest requestBody = new CardListRequest();
            CardListRequest.Settings settings = new CardListRequest.Settings();
            CardListRequest.Cursor cursor = new CardListRequest.Cursor();
            cursor.setLimit(limit);
            cursor.setUpdatedAt(updatedAt);
            cursor.setNmID(nmID);
            settings.setCursor(cursor);
            settings.setFilter(new CardListRequest.Filter());
            requestBody.setSettings(settings);

            HttpEntity<CardListRequest> entity = new HttpEntity<>(requestBody, createHeaders(token));

            try {
                rateLimiter.acquire();
                ResponseEntity<CardListResponse> response = restTemplate.postForEntity(url, entity, CardListResponse.class);
                CardListResponse resData = response.getBody();
                if (resData == null || resData.getCards() == null || resData.getCards().isEmpty()) {
                    emptyStreak++;
                    log.info("✅ 本页为空（连续 {} 次），结束分页，总计 {} 条", emptyStreak, allCards.size());
                    if (emptyStreak >= 2) return allCards;
                    // 不要立即退出：第一次空可能因为 limit 太大但只有 100 条，先跳一下 cursor
                    updatedAt = null;
                    nmID = null;
                    continue;
                }

                int before = allCards.size();
                CardListResponse.Card lastCard = null;
                for (CardListResponse.Card card : resData.getCards()) {
                    Long currentNmId = card.getNmID();
                    if (currentNmId == null || seenNmIds.add(currentNmId)) {
                        allCards.add(card);
                    }
                    lastCard = card;
                }
                int added = allCards.size() - before;
                log.info("✅ 本页拉取 {} 条，累计 {} 条", added, allCards.size());

                if (lastCard == null || lastCard.getNmID() == null) {
                    log.info("✅ 最后一条没有 nmID，结束分页，总计 {} 条", allCards.size());
                    return allCards;
                }

                // 进度检查：cursor 没推进就死循环退出
                if (lastCard.getNmID().equals(prevNmId) && java.util.Objects.equals(lastCard.getUpdatedAt(), prevUpdatedAt)) {
                    noProgressStreak++;
                    log.warn("⚠️ cursor 未推进，连续 {} 次，结束翻页", noProgressStreak);
                    if (noProgressStreak >= 2) return allCards;
                } else {
                    noProgressStreak = 0;
                    prevNmId = lastCard.getNmID();
                    prevUpdatedAt = lastCard.getUpdatedAt();
                }

                if (added < limit) {
                    log.info("✅ 本页不足 {} 条（{} 条），推断已到末页，总计 {} 条", limit, added, allCards.size());
                    return allCards;
                }

                updatedAt = lastCard.getUpdatedAt();
                nmID = lastCard.getNmID();
                emptyStreak = 0;
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 分页查询商品列表失败: ", e);
                return allCards;
            }
        }
    }

    public List<CardListResponse.Card> getCardsList(int limit) {
        return getCardsList(limit, null);
    }

    public List<CardListResponse.Card> getCardsList(int limit, String token) {
        List<CardListResponse.Card> allCards = getAllCards(token);
        if (allCards.isEmpty()) {
            return Collections.emptyList();
        }
        return allCards.size() <= limit ? allCards : allCards.subList(0, limit);
    }

    // ==================== 5. 查询仓库库存 ====================
    public List<Map<String, Object>> getWarehouseStocksByWarehouse(List<String> skus, String token) {
        List<Map<String, Object>> result = new ArrayList<>();
        if (skus == null || skus.isEmpty()) return result;
        for (Map<String, Object> warehouse : getWarehouses(token)) {
            Long id = parseLong(warehouse.get("id"));
            if (id == null || id <= 0) continue;
            Map<String, Integer> stocks = new java.util.HashMap<>();
            for (int i = 0; i < skus.size(); i += 100) {
                Map<String, Integer> part = fetchWarehouseStocks(id, skus.subList(i, Math.min(i + 100, skus.size())), token);
                if (part != null) part.forEach((sku, amount) -> stocks.merge(sku, amount, Integer::sum));
            }
            Map<String, Object> row = new java.util.LinkedHashMap<>();
            row.put("warehouseId", id);
            row.put("warehouseName", warehouse.getOrDefault("name", warehouse.getOrDefault("warehouseName", String.valueOf(id))));
            row.put("stocks", stocks);
            result.add(row);
        }
        return result;
    }

    public Map<String, Integer> getWarehouseStocks(List<String> skus) {
        return getWarehouseStocks(skus, null);
    }

    public Map<String, Integer> getWarehouseStocks(List<String> skus, String token) {
        if (skus == null || skus.isEmpty()) {
            log.warn("⚠️ skus 为空，无法查询库存");
            return Collections.emptyMap();
        }
        List<Map<String, Object>> warehouses = getWarehouses(token);
        if (warehouses == null || warehouses.isEmpty()) {
            log.warn("⚠️ 未获取到仓库列表，无法查询库存");
            return Collections.emptyMap();
        }

        Map<String, Integer> merged = new java.util.HashMap<>();
        int batchSize = 100;
        for (Map<String, Object> warehouse : warehouses) {
            Object warehouseIdValue = warehouse.get("id");
            if (warehouseIdValue == null) continue;
            Long currentWarehouseId = parseLong(warehouseIdValue);
            if (currentWarehouseId == null || currentWarehouseId <= 0) continue;
            log.info("📦 查询仓库库存：warehouseId={}", currentWarehouseId);
            for (int i = 0; i < skus.size(); i += batchSize) {
                int end = Math.min(i + batchSize, skus.size());
                Map<String, Integer> batchStocks = fetchWarehouseStocks(currentWarehouseId, skus.subList(i, end), token);
                if (batchStocks != null) {
                    batchStocks.forEach((sku, amount) -> merged.merge(sku, amount, Integer::sum));
                }
            }
        }
        log.info("✅ 多仓库库存查询完成，仓库数={}，合并 {} 个 SKU", warehouses.size(), merged.size());
        return merged;
    }

    public List<Map<String, Object>> getWarehouses() {
        return getWarehouses(null);
    }

    public List<Map<String, Object>> getWarehouses(String token) {
        String url = MARKETPLACE_BASE_URL + "/api/v3/warehouses";
        HttpEntity<String> entity = new HttpEntity<>(createHeaders(token));
        log.info("🏬 正在获取仓库列表...");

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                ResponseEntity<List> response = restTemplate.exchange(url, HttpMethod.GET, entity, List.class);
                List<Map<String, Object>> warehouses = response.getBody();
                return warehouses == null ? Collections.emptyList() : warehouses;
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 获取仓库列表失败: ", e);
                return Collections.emptyList();
            }
        }
        return Collections.emptyList();
    }

    public Map<String, Integer> fetchWarehouseStocks(Long warehouseId, List<String> skus) {
        return fetchWarehouseStocks(warehouseId, skus, null);
    }

    public boolean updateStocks(Long warehouseId, List<Map<String, Object>> stocks, String token) {
        if (stocks == null || stocks.isEmpty()) {
            log.warn("⚠️ 库存更新请求为空，跳过");
            return true;
        }
        // 官方接口单批上限 1000 条，超出需分批（每批之间 200ms）
        final int batchSize = 1000;
        final long intervalMs = 200L;
        String url = MARKETPLACE_BASE_URL + "/api/v3/stocks/" + warehouseId;
        HttpHeaders headers = createHeaders(token);
        headers.setContentType(MediaType.APPLICATION_JSON);

        int total = stocks.size();
        int sent = 0;
        boolean allOk = true;
        while (sent < total) {
            int end = Math.min(sent + batchSize, total);
            List<Map<String, Object>> batch = stocks.subList(sent, end);
            try {
                rateLimiter.acquire();
                HttpEntity<List<Map<String, Object>>> entity = new HttpEntity<>(batch, headers);
                restTemplate.exchange(url, HttpMethod.PUT, entity, Void.class);
                log.info("✅ 库存批量更新成功，warehouseId={}，本批 {}/{} (累计 {}/{})",
                        warehouseId, batch.size(), total, end, total);
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
                log.warn("🚫 库存更新触发限流 (429)，重试本批 {}/{}", end, total);
                try {
                    HttpEntity<List<Map<String, Object>>> entity = new HttpEntity<>(batch, headers);
                    restTemplate.exchange(url, HttpMethod.PUT, entity, Void.class);
                } catch (Exception ex) {
                    log.error("💥 库存批量更新失败，warehouseId={}，本批 {}/{}: ", warehouseId, batch.size(), total, ex);
                    allOk = false;
                }
            } catch (Exception e) {
                log.error("💥 库存批量更新失败，warehouseId={}，本批 {}/{}: ", warehouseId, batch.size(), total, e);
                allOk = false;
            }
            sent = end;
            if (sent < total) {
                try { Thread.sleep(intervalMs); } catch (InterruptedException ie) { Thread.currentThread().interrupt(); }
            }
        }
        return allOk;
    }

    public Map<String, Integer> fetchWarehouseStocks(Long warehouseId, List<String> skus, String token) {
        String url = MARKETPLACE_BASE_URL + "/api/v3/stocks/" + warehouseId;
        Map<String, Object> requestBody = Map.of("skus", skus);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(requestBody, createHeaders(token));
        log.info("🏬 正在查询仓库 [{}] 库存数据，skus数量={}...", warehouseId, skus == null ? 0 : skus.size());

        for (int attempt = 0; attempt < 3; attempt++) {
            rateLimiter.acquire();
            try {
                ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, entity, String.class);
                String rawJson = response.getBody();
                if (rawJson == null || rawJson.isBlank()) {
                    log.warn("⚠️ 仓库库存接口返回空内容");
                    return Collections.emptyMap();
                }

                log.info("📦 仓库库存接口原始返回：{}", rawJson);

                Map<String, Object> body = objectMapper.readValue(rawJson, Map.class);
                Object stocksObj = body.get("stocks");
                if (!(stocksObj instanceof List<?>)) {
                    stocksObj = body.get("data");
                }
                if (!(stocksObj instanceof List<?>)) {
                    stocksObj = body.get("result");
                }
                if (!(stocksObj instanceof List<?> stocksList)) {
                    log.warn("⚠️ 未识别到库存列表字段，返回结构 keys={}", body.keySet());
                    return Collections.emptyMap();
                }

                Map<String, Integer> stocks = new java.util.HashMap<>();
                for (Object item : stocksList) {
                    if (!(item instanceof Map<?, ?> stockItem)) continue;

                    Object skuObj = firstNonNull(stockItem, "sku", "skus", "barcode", "vendorCode", "nmId", "nmID");
                    Object quantityObj = firstNonNull(stockItem, "quantity", "stock", "stocks", "amount", "available");

                    String sku = skuObj == null ? null : String.valueOf(skuObj).trim();
                    Integer quantity = parseInteger(quantityObj);

                    if (sku != null && !sku.isEmpty() && quantity != null) {
                        stocks.put(sku, quantity);
                    }
                }

                log.info("✅ 获取到 {} 个 SKU 库存记录", stocks.size());
                return stocks;
            } catch (HttpClientErrorException.TooManyRequests e) {
                rateLimiter.handle429();
            } catch (Exception e) {
                log.error("💥 查询仓库库存失败: ", e);
                return Collections.emptyMap();
            }
        }
        return Collections.emptyMap();
    }

    private Object firstNonNull(Map<?, ?> map, String... keys) {
        for (String key : keys) {
            Object value = map.get(key);
            if (value != null && !String.valueOf(value).isBlank()) {
                return value;
            }
        }
        return null;
    }

    private Long parseLong(Object value) {
        if (value == null) return null;
        try {
            return Long.parseLong(String.valueOf(value));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Integer parseInteger(Object value) {
        if (value == null) return null;
        try {
            return Integer.parseInt(String.valueOf(value));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    // ==================== 6. 校验商品状态 ====================
    public CardListResponse.Card verifyUploadedCard(String vendorCode) {
        return verifyUploadedCard(vendorCode, null);
    }

    public CardListResponse.Card verifyUploadedCard(String vendorCode, String token) {
        if (vendorCode == null || vendorCode.isBlank()) {
            log.warn("⚠️ verifyUploadedCard: vendorCode 为空");
            return null;
        }
        String target = vendorCode.trim();

        // 第一次尝试
        CardListResponse.Card found = findCardByVendorCode(target, token, 0);
        if (found != null) return found;

        // 第一次找不到时，WB 异步队列可能还在渲染；等 5 秒再翻一次
        log.info("⏳ 第一次未找到 vendorCode={}，5 秒后重试一次…", target);
        try { Thread.sleep(5000); } catch (InterruptedException ie) { Thread.currentThread().interrupt(); }
        return findCardByVendorCode(target, token, 1);
    }

    private CardListResponse.Card findCardByVendorCode(String target, String token, int attempt) {
        List<CardListResponse.Card> cards = getAllCards(token);
        if (cards == null || cards.isEmpty()) {
            log.warn("⏳ [尝试 {}] 商家商品列表为空（翻页未拉到任何卡片）", attempt, cards == null ? 0 : cards.size());
            return null;
        }
        String targetLower = target.toLowerCase();
        for (CardListResponse.Card card : cards) {
            String cv = card.getVendorCode();
            if (cv == null) continue;
            String cvTrim = cv.trim();
            if (cvTrim.equals(target) || cvTrim.equalsIgnoreCase(targetLower)) {
                log.info("✨【真正上架成功】商品卡片已生成！WB 官方编号 (nmID): {}", card.getNmID());
                return card;
            }
        }
        log.info("⏳ [尝试 {}] 在 {} 条卡片中未找到 vendorCode={}，异步队列可能还在渲染，请稍后再查。",
                attempt, cards.size(), target);
        return null;
    }

    public Map<String, Integer> getStocksByWarehouse(List<String> skus) {
        return getStocksByWarehouse(skus, null);
    }

    public Map<String, Integer> getStocksByWarehouse(List<String> skus, String token) {
        return getWarehouseStocks(skus, token);
    }
}
