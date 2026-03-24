# HippoQueryClient initialization and configuration

## Goal
HippoQueryClient initialization and configuration: Implement the HippoQueryClient class to wrap Hippo REST API operations using httpx.

## Acceptance Criteria
- Given a valid HTTP URL for a Hippo API endpoint, when the HippoQueryClient is instantiated, then it establishes a successful HTTP connection within 5 seconds and returns a client object ready for use
- Given an invalid API endpoint (non-existent URL or malformed), when the HippoQueryClient is instantiated, then it raises a ConfigurationError with a descriptive message indicating the endpoint is invalid
- Given proper authentication credentials configured, when the HippoQueryClient makes a request to any API endpoint, then it successfully authenticates and receives a valid HTTP response (status code 200-299)
- Given missing or invalid authentication credentials, when the HippoQueryClient makes a request, then it raises an AuthenticationError with a descriptive message indicating authentication failure
- Given a valid API endpoint URL but no internet connectivity, when the HippoQueryClient is instantiated, then it raises a NetworkError with appropriate timeout handling within 10 seconds
- Given a valid API endpoint that returns HTTP 401 Unauthorized, when the client makes a request, then it handles the authentication failure appropriately and raises an AuthenticationError
- Given a valid API endpoint that returns HTTP 403 Forbidden, when the client makes a request, then it handles the authorization failure appropriately and raises an AuthorizationError
- Given a malformed API endpoint URL with invalid scheme (e.g., ftp://), when the HippoQueryClient is instantiated, then it raises a ConfigurationError indicating unsupported URL scheme
- Given a valid API endpoint with SSL certificate issues, when the client makes a request, then it properly handles SSL verification and either fails with SSL error or allows insecure connection if configured
- Given a valid API endpoint with network timeout of 30 seconds, when the client makes a request, then it times out and raises a TimeoutError with descriptive message

## Constraints
- Complexity: low
