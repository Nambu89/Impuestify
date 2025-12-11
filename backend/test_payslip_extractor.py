"""
Script de prueba para verificar el servicio PayslipExtractor

Este script prueba:
1. Creación de instancia del extractor
2. Validación de patrones regex
3. Conversión de números españoles
4. Generación de resúmenes
"""
import asyncio
import sys
from pathlib import Path

# Añadir backend al path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.payslip_extractor import PayslipExtractor


def test_spanish_number_parsing():
    """Prueba la conversión de números españoles"""
    print("\n" + "="*60)
    print("TEST 1: Conversión de números españoles")
    print("="*60)
    
    extractor = PayslipExtractor()
    
    test_cases = [
        ("1.234,56", 1234.56),
        ("2.500,00", 2500.00),
        ("375,50", 375.50),
        ("15,25", 15.25),
        ("1.000.000,99", 1000000.99),
    ]
    
    all_passed = True
    for spanish_num, expected in test_cases:
        result = extractor._parse_spanish_number(spanish_num)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✅" if passed else "❌"
        print(f"{status} '{spanish_num}' -> {result} (esperado: {expected})")
    
    return all_passed


def test_effective_tax_rate():
    """Prueba el cálculo del tipo efectivo de IRPF"""
    print("\n" + "="*60)
    print("TEST 2: Cálculo de tipo efectivo de IRPF")
    print("="*60)
    
    extractor = PayslipExtractor()
    
    test_cases = [
        (375.00, 2500.00, 15.0),   # 375/2500 * 100 = 15%
        (450.00, 3000.00, 15.0),   # 450/3000 * 100 = 15%
        (200.00, 2000.00, 10.0),   # 200/2000 * 100 = 10%
    ]
    
    all_passed = True
    for irpf, gross, expected in test_cases:
        result = extractor.calculate_effective_tax_rate(irpf, gross)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✅" if passed else "❌"
        print(f"{status} IRPF: {irpf}€, Bruto: {gross}€ -> {result}% (esperado: {expected}%)")
    
    return all_passed


def test_summary_generation():
    """Prueba la generación de resúmenes"""
    print("\n" + "="*60)
    print("TEST 3: Generación de resúmenes")
    print("="*60)
    
    extractor = PayslipExtractor()
    
    sample_data = {
        'period_month': 12,
        'period_year': 2024,
        'gross_salary': 2500.00,
        'net_salary': 1850.50,
        'irpf_amount': 375.00,
        'irpf_percentage': 15.0,
        'ss_contribution': 150.00
    }
    
    summary = extractor.generate_summary(sample_data)
    print(f"\nDatos de entrada:")
    for key, value in sample_data.items():
        print(f"  {key}: {value}")
    
    print(f"\nResumen generado:")
    print(f"  {summary}")
    
    # Verificar que el resumen contiene información clave
    has_period = "12/2024" in summary
    has_gross = "2500.00" in summary
    has_net = "1850.50" in summary
    has_irpf = "375.00" in summary
    
    all_present = has_period and has_gross and has_net and has_irpf
    status = "✅" if all_present else "❌"
    print(f"\n{status} Resumen contiene todos los campos esperados")
    
    return all_present


def test_regex_patterns():
    """Prueba los patrones regex con texto de ejemplo"""
    print("\n" + "="*60)
    print("TEST 4: Patrones regex")
    print("="*60)
    
    extractor = PayslipExtractor()
    
    # Texto de ejemplo simulando una nómina
    sample_text = """
    NÓMINA DEL MES
    Periodo: 12/2024
    
    DATOS DE LA EMPRESA
    Razón Social: EJEMPLO EMPRESA SL
    CIF: B12345678
    
    DATOS DEL TRABAJADOR
    Nombre: JUAN PEREZ GARCIA
    DNI: 12345678A
    Número Seguridad Social: 123456789012
    
    DEVENGOS
    Salario Base: 1.800,00 €
    Total Devengado: 2.500,00 €
    
    DEDUCCIONES
    I.R.P.F. (15,00%): 375,00 €
    Contingencias Comunes: 125,00 €
    Desempleo: 41,25 €
    
    LÍQUIDO A PERCIBIR: 1.850,50 €
    """
    
    extracted = extractor._parse_payslip_data(sample_text)
    
    print(f"\nCampos extraídos ({len(extracted)}):")
    for key, value in extracted.items():
        print(f"  ✓ {key}: {value}")
    
    # Verificar campos clave
    expected_fields = ['period_month', 'period_year', 'company_name', 'company_cif', 
                      'employee_name', 'employee_nif', 'gross_salary', 'net_salary']
    
    found_fields = sum(1 for field in expected_fields if field in extracted)
    total_fields = len(expected_fields)
    
    print(f"\n{'✅' if found_fields == total_fields else '⚠️'} Extraídos {found_fields}/{total_fields} campos esperados")
    
    return found_fields >= total_fields * 0.7  # Al menos 70% de campos


async def test_pdf_extraction():
    """Prueba la extracción de un PDF (si existe)"""
    print("\n" + "="*60)
    print("TEST 5: Extracción de PDF")
    print("="*60)
    
    # Buscar un PDF de prueba
    test_pdf_paths = [
        "test_nomina.pdf",
        "../test_nomina.pdf",
        "../../test_nomina.pdf",
    ]
    
    pdf_path = None
    for path in test_pdf_paths:
        if Path(path).exists():
            pdf_path = path
            break
    
    if not pdf_path:
        print("⚠️  No se encontró PDF de prueba")
        print("   Puedes crear uno en: backend/test_nomina.pdf")
        return None
    
    print(f"📄 Usando PDF: {pdf_path}")
    
    extractor = PayslipExtractor()
    result = await extractor.extract_from_pdf(pdf_path)
    
    print(f"\nEstado: {result.get('extraction_status')}")
    
    if result.get('extraction_status') == 'completed':
        print(f"Hash: {result.get('file_hash', 'N/A')[:16]}...")
        
        # Mostrar campos extraídos (sin el texto completo)
        print("\nDatos extraídos:")
        for key, value in result.items():
            if key not in ['full_text', 'file_hash']:
                print(f"  {key}: {value}")
        
        # Generar resumen
        summary = extractor.generate_summary(result)
        print(f"\nResumen: {summary}")
        
        # Estadísticas
        stats = extractor.get_extraction_stats(result)
        print(f"\nEstadísticas:")
        print(f"  Campos totales: {stats['total_fields']}")
        print(f"  Campos extraídos: {stats['extracted_fields']}")
        print(f"  Tasa de extracción: {stats['extraction_rate']}%")
        
        return True
    else:
        print(f"❌ Error: {result.get('error')}")
        return False


async def main():
    """Ejecuta todos los tests"""
    print("\n" + "="*60)
    print("🧪 TESTS DEL SERVICIO PAYSLIP EXTRACTOR")
    print("="*60)
    
    results = []
    
    # Tests síncronos
    results.append(("Conversión números españoles", test_spanish_number_parsing()))
    results.append(("Cálculo tipo efectivo IRPF", test_effective_tax_rate()))
    results.append(("Generación de resúmenes", test_summary_generation()))
    results.append(("Patrones regex", test_regex_patterns()))
    
    # Test asíncrono (PDF)
    pdf_result = await test_pdf_extraction()
    if pdf_result is not None:
        results.append(("Extracción de PDF", pdf_result))
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron correctamente!")
    elif passed >= total * 0.7:
        print("\n⚠️  La mayoría de tests pasaron, pero hay algunos fallos")
    else:
        print("\n❌ Varios tests fallaron, revisa la implementación")


if __name__ == "__main__":
    asyncio.run(main())
