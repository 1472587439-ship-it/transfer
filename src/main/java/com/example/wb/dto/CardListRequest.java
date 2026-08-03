package com.example.wb.dto;

import lombok.Data;

// ---- 商品列表查询实体 ----
@Data
public class CardListRequest {
    private Settings settings;

    @Data
    public static class Settings {
        private Cursor cursor;
        private Filter filter;
    }

    @Data
    public static class Cursor {
        private int limit = 100;
        private String updatedAt;
        private Long nmID;
    }

    @Data
    public static class Filter {
        private int withPhoto = -1;
    }
}
