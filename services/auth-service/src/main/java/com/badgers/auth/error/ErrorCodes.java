package com.badgers.auth.error;

public final class ErrorCodes {
    private ErrorCodes() {}

    public static final String AUTH_EMAIL_ALREADY_REGISTERED = "AUTH_EMAIL_ALREADY_REGISTERED";
    public static final String AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS";
    public static final String AUTH_INVALID_REFRESH_TOKEN = "AUTH_INVALID_REFRESH_TOKEN";
    public static final String AUTH_REFRESH_SESSION_NOT_FOUND = "AUTH_REFRESH_SESSION_NOT_FOUND";
    public static final String AUTH_USER_NOT_FOUND = "AUTH_USER_NOT_FOUND";
    public static final String AUTH_AUTHENTICATION_REQUIRED = "AUTH_AUTHENTICATION_REQUIRED";
    public static final String AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN";
    public static final String AUTH_INVALID_TOKEN_TYPE = "AUTH_INVALID_TOKEN_TYPE";
    public static final String AUTH_TOKEN_SUBJECT_INVALID = "AUTH_TOKEN_SUBJECT_INVALID";
    public static final String AUTH_TOKEN_SESSION_INVALID = "AUTH_TOKEN_SESSION_INVALID";
    public static final String VALIDATION_ERROR = "VALIDATION_ERROR";
    public static final String INVALID_REQUEST_BODY = "INVALID_REQUEST_BODY";
    public static final String INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR";
}
