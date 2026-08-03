package com.example.wb.dto;

import lombok.Data;
import java.util.List;

// ---- 上架商品 Payload 实体 ----
@Data
public class ProductUploadPayload {
    private Integer subjectID;
    private List<Variant> variants;

    @Data
    public static class Variant {
        private String vendorCode;
        private String title;
        private String description;
        private String brand;
        private List<String> skus; // 条形码列表
        private Dimensions dimensions; // 包装尺寸和重量
    }

    @Data
    public static class Dimensions {
        private Integer length; // 厘米，1~700
        private Integer width;  // 厘米，1~700
        private Integer height; // 厘米，1~700
        private Integer weightBrutto; // 克，必须大于 0
    }
}
