# Security Policy - TaxIA

## 🛡️ Security Overview

TaxIA implements enterprise-grade security measures to protect user data and prevent malicious attacks. This document outlines our security architecture **without revealing implementation details that could be exploited**.

---

## 🔒 Protection Layers

### 1. Input Validation

**What we protect against**:
- SQL injection attacks (direct and indirect)
- Malicious file uploads
- Cross-site scripting (XSS)
- Path traversal attempts

**How**:
- Multi-layer input sanitization
- File content verification
- Size and format restrictions
- Industry-standard pattern detection

### 2. AI Safety & Compliance

**What we protect against**:
- Tax evasion advice generation
- LLM hallucinations
- Off-topic or harmful queries
- Toxic language

**How**:
- Input and output validation
- Source attribution requirements
- Automated disclaimer insertion
- Topic relevance checking

### 3. Rate Limiting & DDoS Protection

**What we protect against**:
- Distributed denial-of-service (DDoS)
- Brute force attacks
- API abuse
- Cost explosion (Azure API calls)

**How**:
- Per-endpoint rate limits
- Automatic IP blocking after violations
- Progressive penalties
- Intelligent caching

### 4. Authentication & Authorization

**What we protect against**:
- Unauthorized access
- Session hijacking
- Privilege escalation

**How**:
- JWT-based authentication
- Role-based access control (RBAC)
- Secure password hashing
- Token expiration

---

## 🚨 Reporting Security Vulnerabilities

We take security seriously. If you discover a vulnerability:

### **DO**:
1. **Email us privately** at: [security@your-domain.com](mailto:security@your-domain.com)
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)
3. Allow us **reasonable time** to fix before public disclosure (typically 90 days)

### **DON'T**:
- ❌ Post vulnerabilities publicly (GitHub Issues, social media)
- ❌ Exploit the vulnerability beyond proof-of-concept
- ❌ Access other users' data

We appreciate responsible disclosure and will acknowledge contributors.

---

## 🔍 Security Testing

### Automated Tests

We maintain comprehensive security test suites:

```bash
# Run security tests
cd backend
pytest tests/test_security.py -v
```

**What we test**:
- SQL injection patterns
- File upload validation
- Guardrails effectiveness
- Rate limiting enforcement
- Security headers presence

### Manual Review

- Regular code audits
- Dependency vulnerability scanning
- Penetration testing (on request)

---

## 📊 Security Monitoring

### Logs We Collect

For security purposes, we log:
- Failed authentication attempts
- Rate limit violations
- IP blocks/unblocks
- Suspicious input patterns
- File upload rejections

**We do NOT log**:
- Passwords (ever)
- Full conversation content (only metadata)
- Personal data beyond what's necessary

### Incident Response

In case of a security incident:
1. **Detection**: Automated alerts notify our team
2. **Containment**: Affected systems isolated immediately
3. **Investigation**: Root cause analysis
4. **Remediation**: Patch deployed
5. **Communication**: Users notified if data was affected

---

## 🔐 Data Protection

### What We Store

- User credentials (hashed)
- Conversation metadata
- Uploaded notification PDFs (temporary)
- Usage statistics (anonymized)

### What We DON'T Store

- Passwords in plaintext
- Credit card information
- Full conversation content permanently
- PII beyond authentication needs

### Data Retention

- **Conversations**: Retained until user deletion
- **Uploaded files**: Deleted after processing
- **Logs**: Retained for 90 days maximum
- **Cached data**: Auto-expires (1 hour TTL)

---

## 🌐 Infrastructure Security

### External Services

We use industry-leading secure services:
- **Azure AI**: SOC 2, ISO 27001 compliant
- **Turso Database**: Encrypted at rest and in transit
- **Upstash Redis**: TLS encryption
- **Railway**: Secure deployment platform

### Network Security

- HTTPS/TLS encryption (required)
- CORS restrictions
- Security headers (CSP, HSTS, etc.)
- Cloudflare DDoS protection (recommended)

---

## 🛠️ Security Best Practices for Users

### Recommendations

1. **Use strong passwords**: Minimum 8 characters, mix of types
2. **Don't share credentials**: Each user should have their own account
3. **Verify sources**: Check that responses cite official documents
4. **Report suspicious behavior**: Contact us if something seems off
5. **Keep sessions secure**: Log out on shared devices

### What to NEVER share with TaxIA

Even though we filter PII, please avoid:
- Full credit card numbers
- Bank account credentials
- Government ID numbers (DNI/NIE) unless necessary
- Passwords to other services

---

## 📅 Security Updates

### Update Policy

- **Critical vulnerabilities**: Patched within 24-48 hours
- **High-severity**: Patched within 1 week
- **Medium/Low**: Included in regular updates

### Dependency Management

- Automated dependency scans (GitHub Dependabot)
- Monthly security audits
- Immediate response to CVEs affecting our stack

---

## 🎯 Compliance

### Current Status

- **GDPR**: Privacy-first design
- **OWASP**: Following Top 10 security practices
- **Azure**: Compliant with Azure security baselines

### Future Goals

- ISO 27001 certification (if scale requires)
- SOC 2 compliance
- Regular third-party security audits

---

## 📞 Contact

**Security Team**: security@your-domain.com  
**General Support**: support@your-domain.com  
**Emergency**: For critical security incidents only

---

## ⚖️ Disclaimer

While we implement robust security measures, **no system is 100% secure**. We:
- Make our best effort to protect your data
- Respond promptly to discovered vulnerabilities
- Continuously improve our security posture

**By using TaxIA, you acknowledge** that you use the service at your own risk and should not share highly sensitive information without necessary precautions.

---

**Last Updated**: 2024-12-09  
**Version**: 1.0
