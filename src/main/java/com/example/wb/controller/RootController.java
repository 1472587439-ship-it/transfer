package com.example.wb.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class RootController {

    @GetMapping("/")
    public Map<String, Object> root() {
        return Map.of(
                "name", "WB 商品管理系统 API",
                "status", "running",
                "frontend", "请通过 Vite 前端访问：http://localhost:5173",
                "api", "/api/wb/* 与 /api/shop/*"
        );
    }
}