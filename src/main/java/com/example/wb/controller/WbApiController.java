package com.example.wb.controller;

import com.example.wb.dto.ApiResult;
import com.example.wb.dto.CardListResponse;
import com.example.wb.dto.ProductUploadPayload;
import com.example.wb.service.WbApiService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/wb")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class WbApiController {

    private final WbApiService wbApiService;

    /** 生成条形码 */
    @PostMapping("/barcodes")
    public ApiResult<List<String>> generateBarcodes(@RequestHeader(value = "Authorization", required = false) String token,
                                                      @RequestBody Map<String, Integer> body) {
        int count = body.getOrDefault("count", 1);
        if (count < 1 || count > 100) {
            return ApiResult.fail("count 需在 1～100 之间");
        }
        List<String> barcodes = wbApiService.generateWbBarcodes(count, token);
        if (barcodes.isEmpty()) {
            return ApiResult.fail("申请条形码失败，请检查 Token 或稍后重试");
        }
        return ApiResult.ok("成功申请 " + barcodes.size() + " 个条形码", barcodes);
    }

    /** 提交商品卡片 */
    @PostMapping("/cards/upload")
    public ApiResult<Void> uploadCard(@RequestHeader(value = "Authorization", required = false) String token,
                                       @RequestBody List<ProductUploadPayload> payload) {
        if (payload == null || payload.isEmpty()) {
            return ApiResult.fail("商品数据不能为空");
        }
        boolean ok = wbApiService.uploadCard(payload, token);
        return ok ? ApiResult.ok("卡片上传任务已提交", null) : ApiResult.fail("卡片上传失败，请查看后端日志");
    }

    /** 上传商品图片（v3 接口需 nmID，可先通过「校验状态」按货号查到 nmID） */
    @PostMapping(value = "/media/file", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ApiResult<Void> uploadImage(
            @RequestHeader(value = "Authorization", required = false) String token,
            @RequestParam("nmId") Long nmId,
            @RequestParam("photoOrder") int photoOrder,
            @RequestParam("file") MultipartFile file) throws IOException {

        if (nmId == null || nmId <= 0) {
            return ApiResult.fail("nmID 不能为空，请先校验上架状态获取官方编号");
        }
        if (photoOrder < 1 || photoOrder > 30) {
            return ApiResult.fail("图片序号需在 1～30 之间");
        }
        if (file == null || file.isEmpty()) {
            return ApiResult.fail("请选择图片文件");
        }

        String suffix = guessSuffix(file.getOriginalFilename());
        File temp = Files.createTempFile("wb-img-", suffix).toFile();
        try {
            file.transferTo(temp);
            boolean ok = wbApiService.uploadProductImage(nmId, photoOrder, temp, token);
            return ok ? ApiResult.ok("图片上传成功", null) : ApiResult.fail("图片上传失败");
        } finally {
            //noinspection ResultOfMethodCallIgnored
            temp.delete();
        }
    }

    /** 通过图片 URL 上架（会替换该 nmID 下全部媒体） */
    @PostMapping("/media/save")
    public ApiResult<Void> uploadImageByUrls(@RequestHeader(value = "Authorization", required = false) String token,
                                             @RequestBody Map<String, Object> body) {
        Object nmIdObj = body.get("nmId");
        Object dataObj = body.get("data");

        if (nmIdObj == null) {
            return ApiResult.fail("nmID 不能为空，请先校验上架状态获取官方编号");
        }
        long nmId;
        try {
            nmId = Long.parseLong(String.valueOf(nmIdObj));
        } catch (NumberFormatException e) {
            return ApiResult.fail("nmID 格式不正确");
        }
        if (nmId <= 0) {
            return ApiResult.fail("nmID 不能为空，请先校验上架状态获取官方编号");
        }

        List<String> urls = new java.util.ArrayList<>();
        if (dataObj instanceof List<?> list) {
            for (Object item : list) {
                if (item != null) {
                    String u = String.valueOf(item).trim();
                    if (!u.isEmpty()) urls.add(u);
                }
            }
        }
        if (urls.isEmpty()) {
            return ApiResult.fail("请至少提供一个图片 URL");
        }

        boolean ok = wbApiService.uploadProductImageByUrls(nmId, urls, token);
        return ok ? ApiResult.ok("URL 图片上传成功", null) : ApiResult.fail("URL 图片上传失败");
    }

    /** 查询上架失败详情 */
    @PostMapping("/cards/errors/detailed")
    public ApiResult<List<Object>> checkErrorsDetailed(@RequestHeader(value = "Authorization", required = false) String token) {
        return ApiResult.ok("错误查询完成", wbApiService.checkErrorsDetailed(token));
    }

    /** 检查后台错误 */
    @PostMapping("/cards/errors")
    public ApiResult<List<Object>> checkErrors(@RequestHeader(value = "Authorization", required = false) String token) {
        List<Object> errors = wbApiService.checkErrors(token);
        if (errors == null) {
            return ApiResult.ok("后台无错误日志", List.of());
        }
        return ApiResult.ok("发现 " + errors.size() + " 条记录", errors);
    }

    /** 设置商品价格 */
    @PostMapping("/prices")
    public ApiResult<Void> setPrices(@RequestHeader(value = "Authorization", required = false) String token,
                                      @RequestBody Map<String, Object> body) {
        Object dataObj = body.get("data");
        if (!(dataObj instanceof List<?> list) || list.isEmpty() || list.size() > 1000) {
            return ApiResult.fail("价格数据数量必须在 1~1000 之间");
        }
        List<Map<String, Object>> prices = new java.util.ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> map)) return ApiResult.fail("价格项格式错误");
            Object nmIdValue = map.get("nmID");
            Object priceValue = map.get("price");
            Object discountValue = map.get("discount");
            if (nmIdValue == null || (priceValue == null && discountValue == null)) {
                return ApiResult.fail("nmID 不能为空，price 和 discount 不能同时为空");
            }
            try {
                long nmID = Long.parseLong(String.valueOf(nmIdValue));
                if (nmID <= 0) return ApiResult.fail("nmID 必须大于 0");
                Map<String, Object> p = new java.util.LinkedHashMap<>();
                p.put("nmID", nmID);
                if (priceValue != null) {
                    int price = Integer.parseInt(String.valueOf(priceValue));
                    if (price < 0) return ApiResult.fail("price 不能为负数");
                    p.put("price", price);
                }
                if (discountValue != null) {
                    int discount = Integer.parseInt(String.valueOf(discountValue));
                    if (discount < 0 || discount > 100) return ApiResult.fail("discount 必须在 0~100 之间");
                    p.put("discount", discount);
                }
                prices.add(p);
            } catch (NumberFormatException e) {
                return ApiResult.fail("nmID、price、discount 必须是整数");
            }
        }
        boolean ok = wbApiService.setProductPrices(prices, token);
        return ok ? ApiResult.ok("价格设置成功", null) : ApiResult.fail("价格设置失败");
    }

    /** 获取商品原价、折扣和现价 */
    @PostMapping("/prices/query")
    public ApiResult<Map<String, Object>> queryPrices(@RequestHeader(value = "Authorization", required = false) String token,
                                                       @RequestBody Map<String, Object> body) {
        List<Long> nmIds = new java.util.ArrayList<>();
        Object ids = body.get("filterNmID");
        if (ids instanceof List<?> list) {
            for (Object id : list) {
                try {
                    long value = Long.parseLong(String.valueOf(id));
                    if (value > 0 && !nmIds.contains(value)) nmIds.add(value);
                } catch (NumberFormatException ignored) {
                }
            }
        }
        if (nmIds.isEmpty()) return ApiResult.fail("filterNmID 不能为空且必须为正整数");
        return ApiResult.ok("价格查询成功", wbApiService.getGoodsPrices(nmIds, token));
    }

    /** 获取当前商家商品列表 */
    @GetMapping("/cards/list")
    public ApiResult<List<CardListResponse.Card>> getCardsList(@RequestHeader(value = "Authorization", required = false) String token,
                                                                @RequestParam(defaultValue = "100") int limit) {
        if (limit < 1 || limit > 1000) {
            return ApiResult.fail("limit 需在 1～1000 之间");
        }
        List<CardListResponse.Card> cards = wbApiService.getCardsList(limit, token);
        return ApiResult.ok("成功获取商品列表，共 " + cards.size() + " 条", cards);
    }

    /** 校验商品是否已上架 */
    @PostMapping("/cards/verify")
    public ApiResult<CardListResponse.Card> verifyCard(@RequestHeader(value = "Authorization", required = false) String token,
                                                        @RequestBody Map<String, String> body) {
        String vendorCode = body.get("vendorCode");
        if (vendorCode == null || vendorCode.isBlank()) {
            return ApiResult.fail("货号 vendorCode 不能为空");
        }
        CardListResponse.Card card = wbApiService.verifyUploadedCard(vendorCode, token);
        if (card == null) {
            return ApiResult.fail("暂未找到该货号，异步队列可能仍在处理");
        }
        return ApiResult.ok("商品已上架", card);
    }

    @PostMapping("/stocks/warehouses")
    public ApiResult<List<Map<String, Object>>> getWarehouseStocksByWarehouse(@RequestHeader(value = "Authorization", required = false) String token,
                                                                                @RequestBody Map<String, Object> body) {
        List<String> skus = new java.util.ArrayList<>();
        Object value = body.get("skus");
        if (value instanceof List<?> list) list.forEach(item -> { if (item != null) skus.add(String.valueOf(item)); });
        return ApiResult.ok("成功获取各仓库库存", wbApiService.getWarehouseStocksByWarehouse(skus, token));
    }

    /** 同步仓库库存到商品列表页使用 */
    @PostMapping("/stocks/warehouse")
    public ApiResult<Map<String, Integer>> getWarehouseStocks(@RequestHeader(value = "Authorization", required = false) String token,
                                                               @RequestBody Map<String, Object> body) {
        Object skusObj = body.get("skus");
        List<String> skus = new java.util.ArrayList<>();
        if (skusObj instanceof List<?> list) {
            for (Object item : list) {
                if (item != null) {
                    String sku = String.valueOf(item).trim();
                    if (!sku.isEmpty()) skus.add(sku);
                }
            }
        }
        Map<String, Integer> stocks = wbApiService.getStocksByWarehouse(skus, token);
        return ApiResult.ok("成功获取仓库库存", stocks);
    }

    /**
     * 更新仓库商品库存
     * 请求体：{ "stocks": [ { "sku": "...", "amount": 10 } | { "chrtId": 123, "amount": 10 } ... ] }
     * 文档限流：1 分钟 300 次 / 间隔 200ms / 突发 20 次。
     * 实际请求中若 stocks 超过 1000 条，按 1000 条/批 自动分批，每批间隔 200ms。
     */
    @PutMapping("/stocks/{warehouseId}")
    public ApiResult<Void> updateStocks(@RequestHeader(value = "Authorization", required = false) String token,
                                        @PathVariable Long warehouseId,
                                        @RequestBody Map<String, Object> body) {
        Object stocksObj = body.get("stocks");
        if (!(stocksObj instanceof List<?> list) || list.isEmpty()) {
            return ApiResult.fail("stocks 不能为空");
        }
        List<Map<String, Object>> stocks = new java.util.ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> map)) return ApiResult.fail("库存项格式错误");
            Object amount = map.get("amount");
            if (amount == null) return ApiResult.fail("amount 不能为空");
            Map<String, Object> stockItem = new java.util.LinkedHashMap<>();
            Object sku = map.get("sku");
            Object chrtId = map.get("chrtId");
            if (sku != null && !String.valueOf(sku).isBlank()) {
                stockItem.put("sku", String.valueOf(sku));
            } else if (chrtId != null) {
                stockItem.put("chrtId", Long.parseLong(String.valueOf(chrtId)));
            } else {
                return ApiResult.fail("sku 和 chrtId 至少需要有一个");
            }
            stockItem.put("amount", Integer.parseInt(String.valueOf(amount)));
            stocks.add(stockItem);
        }
        boolean ok = wbApiService.updateStocks(warehouseId, stocks, token);
        return ok ? ApiResult.ok("库存更新成功", null) : ApiResult.fail("库存更新失败");
    }

    /** 获取仓库列表，便于查 warehouseId */
    @GetMapping("/warehouses")
    public ApiResult<List<Map<String, Object>>> getWarehouses(@RequestHeader(value = "Authorization", required = false) String token) {
        List<Map<String, Object>> warehouses = wbApiService.getWarehouses(token);
        return ApiResult.ok("成功获取仓库列表", warehouses);
    }

    private static String guessSuffix(String name) {
        if (name == null || !name.contains(".")) {
            return ".jpg";
        }
        return name.substring(name.lastIndexOf('.'));
    }
}
