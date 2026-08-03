package com.example.wb.controller;

import com.example.wb.dto.ApiResult;
import com.example.wb.service.OutputScannerService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * output 文件夹扫描接口
 * - GET /api/output/list：列出当前所有 w_*.json 中未上架的商品
 * - GET /api/output/page?page=1&size=10：分页获取商品（page 从 1 开始）
 * - GET /api/output/poll?since=ms：长轮询，文件有变更才返回，最多等 30 秒
 * - POST /api/output/mark：标记某个商品已上架到指定店铺（hit 追加店铺名）
 * - GET /api/output/info：获取 output 文件夹路径信息
 */
@RestController
@RequestMapping("/api/output")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class OutputController {

    private final OutputScannerService scannerService;

    @GetMapping("/info")
    public ApiResult<Map<String, Object>> info() {
        Map<String, Object> info = new HashMap<>();
        info.put("dir", scannerService.getOutputDir());
        info.put("pattern", "w_*.json");
        return ApiResult.ok("output 文件夹信息", info);
    }

    @GetMapping("/list")
    public ApiResult<List<OutputScannerService.ProductItem>> list() {
        List<OutputScannerService.ProductItem> items = scannerService.scanAll();
        return ApiResult.ok("已加载 " + items.size() + " 个商品", items);
    }

    @GetMapping("/page")
    public ApiResult<Map<String, Object>> page(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String shopName) {

        if (page < 1) page = 1;
        if (size < 1) size = 10;
        if (size > 100) size = 100;

        List<OutputScannerService.ProductItem> all = scannerService.scanAll(shopName);
        int total = all.size();
        int totalPages = Math.max(1, (int) Math.ceil(total / (double) size));

        int start = (page - 1) * size;
        int end = Math.min(start + size, total);
        List<OutputScannerService.ProductItem> items = start >= total
                ? List.of()
                : all.subList(start, end);

        Map<String, Object> result = new HashMap<>();
        result.put("items", items);
        result.put("total", total);
        result.put("page", page);
        result.put("size", size);
        result.put("totalPages", totalPages);
        result.put("hasNext", page < totalPages);
        result.put("hasPrev", page > 1);
        return ApiResult.ok("第 " + page + "/" + totalPages + " 页，共 " + total + " 个商品", result);
    }

    /**
     * 长轮询：客户端传上次最后修改时间戳（毫秒），
     * 服务端检查文件夹是否有变更；如果没有则最长等 30 秒。
     * 返回的是最新列表（不分页）。
     */
    @GetMapping("/poll")
    public ApiResult<Map<String, Object>> poll(@RequestParam(defaultValue = "0") long since) throws InterruptedException {
        long deadline = System.currentTimeMillis() + 30_000L;
        int changed = 0;
        while (System.currentTimeMillis() < deadline) {
            changed = scannerService.detectChanges();
            if (changed > 0) break;
            Thread.sleep(1500);
        }
        List<OutputScannerService.ProductItem> items = scannerService.scanAll();
        Map<String, Object> result = new HashMap<>();
        result.put("items", items);
        result.put("changed", changed);
        result.put("serverTime", System.currentTimeMillis());
        return ApiResult.ok("轮询完成，商品数=" + items.size(), result);
    }

    @PostMapping("/mark")
    public ApiResult<Void> mark(@RequestBody Map<String, Object> body) {
        String sourceRef = (String) body.get("sourceRef");
        String shopName = (String) body.get("shopName");
        if (sourceRef == null || sourceRef.isBlank()) {
            return ApiResult.fail("sourceRef 不能为空");
        }
        if (shopName == null || shopName.isBlank()) {
            return ApiResult.fail("shopName 不能为空");
        }
        boolean ok = scannerService.markHit(sourceRef, shopName);
        return ok ? ApiResult.ok("已标记 " + shopName, null) : ApiResult.fail("标记失败");
    }
}