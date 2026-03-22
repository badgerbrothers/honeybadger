package com.badgers.auth.service;

import java.util.UUID;

public record JwtUserPrincipal(UUID userId, String email) {}
