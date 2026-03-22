package com.badgers.auth.service;

import com.badgers.auth.config.JwtProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Date;
import java.util.Objects;
import java.util.UUID;
import javax.crypto.SecretKey;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class JwtService {
    private static final String ACCESS_TOKEN_TYPE = "access";
    private static final String REFRESH_TOKEN_TYPE = "refresh";
    private static final String TOKEN_TYPE_CLAIM = "token_type";
    private static final String SESSION_ID_CLAIM = "sid";

    private final JwtProperties jwtProperties;
    private final SecretKey signingKey;

    public JwtService(JwtProperties jwtProperties) {
        this.jwtProperties = jwtProperties;
        this.signingKey = buildSigningKey(jwtProperties);
    }

    public String createAccessToken(UUID userId, String email) {
        Instant now = Instant.now();
        Instant expiresAt = now.plus(jwtProperties.getAccessExpireMinutes(), ChronoUnit.MINUTES);

        return Jwts.builder()
            .id(UUID.randomUUID().toString())
            .subject(userId.toString())
            .issuer(jwtProperties.getIssuer())
            .audience().add(jwtProperties.getAudience()).and()
            .claim(TOKEN_TYPE_CLAIM, ACCESS_TOKEN_TYPE)
            .claim("email", email)
            .issuedAt(Date.from(now))
            .expiration(Date.from(expiresAt))
            .signWith(signingKey)
            .compact();
    }

    public String createRefreshToken(UUID userId, UUID sessionId) {
        Instant now = Instant.now();
        Instant expiresAt = now.plus(jwtProperties.getRefreshExpireDays(), ChronoUnit.DAYS);

        return Jwts.builder()
            .id(UUID.randomUUID().toString())
            .subject(userId.toString())
            .issuer(jwtProperties.getIssuer())
            .audience().add(jwtProperties.getAudience()).and()
            .claim(TOKEN_TYPE_CLAIM, REFRESH_TOKEN_TYPE)
            .claim(SESSION_ID_CLAIM, sessionId.toString())
            .issuedAt(Date.from(now))
            .expiration(Date.from(expiresAt))
            .signWith(signingKey)
            .compact();
    }

    public JwtUserPrincipal parseAccessToken(String token) {
        Claims claims = parseAndValidate(token);
        ensureTokenType(claims, ACCESS_TOKEN_TYPE);
        UUID userId = requiredUuid(claims.getSubject(), "Token subject is missing");
        return new JwtUserPrincipal(userId, claims.get("email", String.class));
    }

    public RefreshTokenClaims parseRefreshToken(String token) {
        Claims claims = parseAndValidate(token);
        ensureTokenType(claims, REFRESH_TOKEN_TYPE);
        UUID userId = requiredUuid(claims.getSubject(), "Token subject is missing");
        UUID sessionId = requiredUuid(claims.get(SESSION_ID_CLAIM, String.class), "Token session is missing");
        return new RefreshTokenClaims(userId, sessionId, claims.getExpiration().toInstant());
    }

    public long accessTokenExpiresInSeconds() {
        return jwtProperties.getAccessExpireMinutes() * 60;
    }

    public long refreshTokenExpiresInDays() {
        return jwtProperties.getRefreshExpireDays();
    }

    private Claims parseAndValidate(String token) {
        try {
            return Jwts.parser()
                .verifyWith(signingKey)
                .requireIssuer(jwtProperties.getIssuer())
                .requireAudience(jwtProperties.getAudience())
                .build()
                .parseSignedClaims(token)
                .getPayload();
        } catch (JwtException | IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid token", ex);
        }
    }

    private static SecretKey buildSigningKey(JwtProperties jwtProperties) {
        if (!Objects.equals(jwtProperties.getAlgorithm(), "HS256")) {
            throw new IllegalArgumentException("Only HS256 is supported");
        }
        byte[] keyBytes = jwtProperties.getSecret().getBytes(StandardCharsets.UTF_8);
        if (keyBytes.length < 32) {
            throw new IllegalArgumentException("JWT_SECRET must be at least 32 bytes for HS256");
        }
        return Keys.hmacShaKeyFor(keyBytes);
    }

    private static void ensureTokenType(Claims claims, String expectedType) {
        String tokenType = claims.get(TOKEN_TYPE_CLAIM, String.class);
        if (!expectedType.equals(tokenType)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid token type");
        }
    }

    private static UUID requiredUuid(String value, String errorMessage) {
        if (value == null || value.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, errorMessage);
        }
        try {
            return UUID.fromString(value);
        } catch (IllegalArgumentException ex) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, errorMessage, ex);
        }
    }

    public record RefreshTokenClaims(UUID userId, UUID sessionId, Instant expiresAt) {}
}
