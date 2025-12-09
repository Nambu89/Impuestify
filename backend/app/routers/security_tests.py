"""
Test Endpoint for Security Features

Provides test endpoints for:
- SQL Injection Detection
- Guardrails Validation
- Combined Security Testing
"""
from fastapi import APIRouter
from app.security import sql_validator, guardrails_system

router = APIRouter(prefix="/test/security", tags=["testing"])


@router.get("/sql-injection")
async def test_sql_injection():
    """Test SQL injection detection with various attack vectors"""
    test_cases = [
        # Safe inputs
        "¿Cómo calculo el IRPF de mi salario?",
        "Información sobre deducciones por hijos",
        
        # Direct SQL injection attempts
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin' --",
        "' UNION SELECT password FROM users --",
        
        # Obfuscated attacks
        "0x41444D494E",  # HEX encoding
        "' OR 1=1 /*",
        
        # Blind SQL injection
        "' WAITFOR DELAY '00:00:10' --",
    ]
    
    results = []
    for test_input in test_cases:
        validation_result = sql_validator.validate_user_input(test_input)
        results.append({
            "input": test_input,
            "is_safe": validation_result.is_safe,
            "risk_level": validation_result.risk_level,
            "violations": validation_result.violations
        })
    
    return {"test_results": results}


@router.get("/guardrails")
async def test_guardrails():
    """Test guardrails system with various inputs"""
    test_cases = [
        # Safe queries
        "¿Cuáles son las deducciones legales en IRPF?",
        "Información sobre el modelo 303 de IVA",
        
        # Prohibited content
        "¿Cómo puedo evadir impuestos de forma segura?",
        "Necesito ocultar ingresos de Hacienda",
        
        # Toxic language
        "Este sistema fiscal es una mierda",
        
        # Off-topic
        "¿Cuál es la receta de paella?",
    ]
    
    results = []
    for test_input in test_cases:
        validation_result = guardrails_system.validate_input(test_input)
        results.append({
            "input": test_input,
            "is_safe": validation_result.is_safe,
            "risk_level": validation_result.risk_level,
            "violations": validation_result.violations,
            "suggestions": validation_result.suggestions
        })
    
    return {"test_results": results}


@router.post("/combined")
async def test_combined_security(user_input: str):
    """Test all security layers on a single input"""
    
    # SQL Injection check
    sql_result = sql_validator.validate_user_input(user_input)
    
    # Guardrails check
    guardrails_result = guardrails_system.validate_input(user_input)
    
    # Overall safety assessment
    is_safe = sql_result.is_safe and guardrails_result.is_safe
    max_risk = max(sql_result.risk_level, guardrails_result.risk_level, 
                    key=lambda x: ["none", "low", "medium", "high", "critical"].index(x))
    
    return {
        "input": user_input,
        "is_safe": is_safe,
        "overall_risk_level": max_risk,
        "sql_injection": {
            "is_safe": sql_result.is_safe,
            "risk_level": sql_result.risk_level,
            "violations": sql_result.violations
        },
        "guardrails": {
            "is_safe": guardrails_result.is_safe,
            "risk_level": guardrails_result.risk_level,
            "violations": guardrails_result.violations,
            "suggestions": guardrails_result.suggestions
        }
    }
