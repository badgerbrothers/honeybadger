package com.badgers.auth.service;

import com.badgers.auth.domain.RefreshTokenSession;
import com.badgers.auth.domain.User;
import com.badgers.auth.dto.AuthTokensResponse;
import com.badgers.auth.dto.LoginRequest;
import com.badgers.auth.dto.LogoutRequest;
import com.badgers.auth.dto.RefreshRequest;
import com.badgers.auth.dto.RegisterRequest;
import com.badgers.auth.dto.UserResponse;
import com.badgers.auth.repository.RefreshTokenSessionRepository;
import com.badgers.auth.repository.UserRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AuthService {
    private final UserRepository userRepository;
    private final RefreshTokenSessionRepository refreshTokenSessionRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthService(
        UserRepository userRepository,
        RefreshTokenSessionRepository refreshTokenSessionRepository,
        PasswordEncoder passwordEncoder,
        JwtService jwtService
    ) {
        this.userRepository = userRepository;
        this.refreshTokenSessionRepository = refreshTokenSessionRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    @Transactional
    public AuthTokensResponse register(RegisterRequest request) {
        String email = normalizeEmail(request.email());
        if (userRepository.findByEmail(email).isPresent()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Email already registered");
        }

        User user = new User(email, passwordEncoder.encode(request.password()));
        userRepository.save(user);
        return issueTokens(user, null);
    }

    @Transactional
    public AuthTokensResponse login(LoginRequest request) {
        String email = normalizeEmail(request.email());
        User user = userRepository.findByEmail(email)
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid credentials"));

        if (!passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid credentials");
        }
        return issueTokens(user, null);
    }

    @Transactional
    public AuthTokensResponse refresh(RefreshRequest request) {
        JwtService.RefreshTokenClaims claims = jwtService.parseRefreshToken(request.refreshToken());
        String refreshTokenHash = hashToken(request.refreshToken());
        RefreshTokenSession currentSession = refreshTokenSessionRepository.findById(claims.sessionId())
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Refresh session not found"));

        Instant now = Instant.now();
        if (!currentSession.getUser().getId().equals(claims.userId())
            || !refreshTokenHash.equals(currentSession.getTokenHash())
            || !currentSession.isActive(now)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Refresh token is invalid");
        }

        currentSession.setRevokedAt(now);
        return issueTokens(currentSession.getUser(), currentSession);
    }

    @Transactional
    public void logout(LogoutRequest request) {
        JwtService.RefreshTokenClaims claims;
        try {
            claims = jwtService.parseRefreshToken(request.refreshToken());
        } catch (ResponseStatusException ex) {
            return;
        }

        String refreshTokenHash = hashToken(request.refreshToken());
        refreshTokenSessionRepository.findById(claims.sessionId()).ifPresent(session -> {
            if (refreshTokenHash.equals(session.getTokenHash()) && session.getRevokedAt() == null) {
                session.setRevokedAt(Instant.now());
                refreshTokenSessionRepository.save(session);
            }
        });
    }

    @Transactional(readOnly = true)
    public UserResponse getUserById(java.util.UUID userId) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
        return new UserResponse(user.getId(), user.getEmail(), user.getCreatedAt());
    }

    private AuthTokensResponse issueTokens(User user, RefreshTokenSession replacedSession) {
        Instant now = Instant.now();
        RefreshTokenSession newSession = new RefreshTokenSession();
        newSession.setUser(user);
        newSession.setIssuedAt(now);
        newSession.setExpiresAt(now.plus(jwtService.refreshTokenExpiresInDays(), ChronoUnit.DAYS));
        refreshTokenSessionRepository.saveAndFlush(newSession);

        String refreshToken = jwtService.createRefreshToken(user.getId(), newSession.getId());
        newSession.setTokenHash(hashToken(refreshToken));
        refreshTokenSessionRepository.save(newSession);

        if (replacedSession != null) {
            replacedSession.setReplacedBySessionId(newSession.getId());
            replacedSession.setRevokedAt(now);
            refreshTokenSessionRepository.save(replacedSession);
        }

        String accessToken = jwtService.createAccessToken(user.getId(), user.getEmail());
        return new AuthTokensResponse(
            accessToken,
            refreshToken,
            "Bearer",
            jwtService.accessTokenExpiresInSeconds()
        );
    }

    private static String normalizeEmail(String value) {
        return value.trim().toLowerCase(Locale.ROOT);
    }

    private static String hashToken(String token) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(token.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hashBytes);
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is unavailable", ex);
        }
    }
}
