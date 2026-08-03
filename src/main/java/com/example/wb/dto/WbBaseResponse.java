package com.example.wb.dto;

import lombok.Data;

// ---- 通用基础响应 ----
@Data
public class WbBaseResponse<T> {
    private Boolean error;
    private String errorText;
    private T data;
}
