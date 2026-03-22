package com.badgers.auth.dto;

public record AuthTokensResponse(
    String accessToken,
    String refreshToken,
    String tokenType,
    long expiresIn
) {}
