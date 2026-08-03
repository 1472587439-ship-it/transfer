package com.example.wb.dto;

import com.fasterxml.jackson.annotation.JsonAnySetter;
import lombok.Data;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

// ---- 商品列表响应实体 ----
@Data
public class CardListResponse {
    private List<Card> cards;
    private Cursor cursor;

    @Data
    public static class Card {
        private String vendorCode;
        private Long nmID;
        private Integer subjectID;
        private String title;
        private String brand;
        private Long brandId;
        private Long imtID;
        private String createdAt;
        private String updatedAt;
        private Object sizes;
        private Object dimensions;
        private Object mediaFiles;
        private Object characteristics;
        private Object skus;
        private Integer stock;
        private final Map<String, Object> extra = new LinkedHashMap<>();

        @JsonAnySetter
        public void addExtra(String key, Object value) {
            extra.put(key, value);
        }
    }

    @Data
    public static class Cursor {
        private String updatedAt;
        private Long nmID;
    }
}

