package com.badgers.auth.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.badgers.auth.config.JwtProperties;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

class JwtServiceTest {
    private JwtService jwtService;

    @BeforeEach
    void setUp() {
        JwtProperties properties = new JwtProperties();
        properties.setSecret("12345678901234567890123456789012");
        properties.setAlgorithm("HS256");
        properties.setIssuer("badgers-auth");
        properties.setAudience("badgers-services");
        properties.setAccessExpireMinutes(30);
        properties.setRefreshExpireDays(7);
        jwtService = new JwtService(properties);
    }

    @Test
    void shouldCreateAndParseAccessToken() {
        UUID userId = UUID.randomUUID();
        String email = "user@example.com";

        String token = jwtService.createAccessToken(userId, email);
        JwtUserPrincipal principal = jwtService.parseAccessToken(token);

        assertEquals(userId, principal.userId());
        assertEquals(email, principal.email());
    }

    @Test
    void shouldCreateAndParseRefreshToken() {
        UUID userId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();

        String token = jwtService.createRefreshToken(userId, sessionId);
        JwtService.RefreshTokenClaims claims = jwtService.parseRefreshToken(token);

        assertEquals(userId, claims.userId());
        assertEquals(sessionId, claims.sessionId());
        assertNotNull(claims.expiresAt());
    }

    @Test
    void shouldRejectWrongTokenType() {
        UUID userId = UUID.randomUUID();
        UUID sessionId = UUID.randomUUID();

        String token = jwtService.createRefreshToken(userId, sessionId);
        assertThrows(ResponseStatusException.class, () -> jwtService.parseAccessToken(token));
    }
}
