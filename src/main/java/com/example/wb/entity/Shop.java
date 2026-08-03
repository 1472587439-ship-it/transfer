package com.example.wb.entity;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class Shop {

    private Long id;
    private String shopName;
    private String apiKey;
    private LocalDateTime createdAt;
}
