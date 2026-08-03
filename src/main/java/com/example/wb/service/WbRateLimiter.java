package com.example.wb.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * WB API 请求节流器
 * 限制规则（按 stocks 接口文档）：
 * - 总限制：每 1 分钟最多 300 次请求
 * - 请求间隔：建议每次请求间隔至少 200 毫秒
 * - 突发并发：允许短时间内最多 20 次突发请求
 */
@Slf4j
@Component
public class WbRateLimiter {

    private static final int MAX_REQUESTS_PER_MINUTE = 300;
    private static final long MIN_INTERVAL_MS = 200L;
    private static final int MAX_BURST = 20;

    private final AtomicInteger requestCount = new AtomicInteger(0);
    private final AtomicLong windowStart = new AtomicLong(System.currentTimeMillis());
    private final AtomicLong lastRequestTime = new AtomicLong(0);
    private final ConcurrentHashMap<Long, AtomicInteger> burstCounter = new ConcurrentHashMap<>();

    public void acquire() {
        acquire(0L);
    }

    public void acquire(long key) {
        AtomicInteger burst = burstCounter.computeIfAbsent(key, k -> new AtomicInteger(0));

        while (true) {
            long now = System.currentTimeMillis();
            long windowAge = now - windowStart.get();

            if (windowAge >= 60_000L) {
                windowStart.set(now);
                requestCount.set(0);
            }

            int currentCount = requestCount.get();
            if (currentCount >= MAX_REQUESTS_PER_MINUTE) {
                long waitMs = 60_000L - windowAge;
                log.warn("⏳ 请求已达每分钟上限 ({}次)，等待 {}ms", MAX_REQUESTS_PER_MINUTE, waitMs);
                sleep(waitMs);
                continue;
            }

            long elapsed = now - lastRequestTime.get();
            if (lastRequestTime.get() > 0 && elapsed < MIN_INTERVAL_MS) {
                long waitMs = MIN_INTERVAL_MS - elapsed;
                sleep(waitMs);
                continue;
            }

            if (burst.get() >= MAX_BURST) {
                log.warn("⏳ 爆发请求已达上限 ({}次)，等待 600ms", MAX_BURST);
                sleep(MIN_INTERVAL_MS);
                burst.set(0);
                continue;
            }

            requestCount.incrementAndGet();
            burst.incrementAndGet();
            lastRequestTime.set(System.currentTimeMillis());

            new Thread(() -> {
                sleepSilent(MIN_INTERVAL_MS * MAX_BURST);
                burst.set(0);
            }).start();

            break;
        }
    }

    public void handle429() {
        log.warn("🚫 收到 429 Too Many Requests，等待 60 秒后重试...");
        sleep(60_000L);
    }

    private void sleep(long ms) {
        if (ms <= 0) return;
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    private void sleepSilent(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
