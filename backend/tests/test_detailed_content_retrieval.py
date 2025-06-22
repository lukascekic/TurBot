import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.document_detail_service import DocumentDetailService
from services.vector_service import VectorService
from services.response_generator import ResponseGenerator
from services.self_querying_service import SelfQueryingService
from openai import AsyncOpenAI
from models.document import SearchQuery

async def test_detailed_content_vs_standard():
    """
    Demonstrira razliku između standardnog i detaljnog pristupa
    kada korisnik pita specifična pitanja o aranžmanima
    """
    print("\n🎯 TESTIRANJE: Detaljni vs Standardni Odgovori")
    print("=" * 70)
    
    # Initialize services
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    vector_service = VectorService()
    detail_service = DocumentDetailService(vector_service)
    response_generator = ResponseGenerator(client)
    self_querying_service = SelfQueryingService(client)
    
    # Test scenarios
    test_scenarios = [
        {
            "scenario": "Specifični datumi polaska",
            "query": "Koji su datumi polaska za Amsterdam u maju?",
            "expected_improvement": "Detaljni datumi polaska umesto općenite informacije"
        },
        {
            "scenario": "Detaljan program aranžmana", 
            "query": "Šta je uključeno u program putovanja za Rim?",
            "expected_improvement": "Konkretan program po danima umesto osnovnih info"
        },
        {
            "scenario": "Precizne cene i opcije",
            "query": "Koliko košta Istanbul putovanje i koje su opcije?", 
            "expected_improvement": "Specifične cene za različite opcije"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}️⃣ SCENARIO: {scenario['scenario']}")
        print(f"Upit: '{scenario['query']}'")
        print("-" * 50)
        
        # Get structured query
        structured_query = await self_querying_service.parse_natural_language_query(scenario['query'])
        
        # Standard approach (current)
        print("📄 STANDARDNI PRISTUP:")
        search_query = SearchQuery(query=scenario['query'], limit=3)
        search_results = vector_service.search(search_query)
        
        # Convert to format expected by response generator
        standard_results = []
        for result in search_results.results:
            standard_results.append({
                'content': result.text[:400],  # Limited content
                'document_name': result.metadata.source_file,
                'metadata': result.metadata.model_dump(),
                'similarity': result.similarity_score
            })
        
        standard_response = await response_generator._generate_natural_response(
            standard_results, structured_query, {}, None, None
        )
        
        print(f"Standardni odgovor: {standard_response[:300]}...")
        print(f"Dostupni sadržaj: {sum(len(r['content']) for r in standard_results)} karaktera")
        
        # Detailed approach (new)
        print("\n📋 DETALJNI PRISTUP:")
        if search_results.results:
            # Get detailed content for top document
            top_document = search_results.results[0].metadata.source_file
            detailed_content = detail_service.get_detailed_content(top_document)
            
            if "error" not in detailed_content:
                print(f"Dokument: {detailed_content['document_name']}")
                print(f"Kompletni sadržaj: {detailed_content['content_length']} karaktera")
                
                structured_info = detailed_content['structured_content']
                print(f"Izvučene cene: {structured_info.get('prices', [])}")
                print(f"Izvučeni datumi: {structured_info.get('dates', [])}")
                print(f"Sekcije: {list(structured_info.get('sections', {}).keys())}")
                
                # Generate detailed response
                detailed_response = await response_generator._generate_detailed_response(
                    [detailed_content], structured_query, None
                )
                
                print(f"\nDetaljni odgovor: {detailed_response.response[:400]}...")
                print(f"Confidence: {detailed_response.confidence:.2f}")
                print(f"Suggested questions: {detailed_response.suggested_questions}")
                
                # Compare
                print("\n⚖️ POREĐENJE:")
                print(f"Standardni - sadržaj: {sum(len(r['content']) for r in standard_results)} chars")
                print(f"Detaljni - sadržaj: {detailed_content['content_length']} chars")
                print(f"Poboljšanje: {detailed_content['content_length'] / sum(len(r['content']) for r in standard_results):.1f}x više informacija")
                
            else:
                print("❌ Greška pri dohvatanju detaljnog sadržaja")
        
        print("\n" + "=" * 70)

async def test_specific_document_queries():
    """
    Test specifičnih upita o dokumentima
    """
    print("\n🔍 TESTIRANJE: Specifični Upiti o Dokumentima")
    print("=" * 60)
    
    vector_service = VectorService()
    detail_service = DocumentDetailService(vector_service)
    
    # Test specific document retrieval
    test_documents = [
        "Amsterdam_PRVI_MAJ_2025_Direktan_let_30.04.-04.05.2025._Cenovnik_1504.pdf",
        "Istanbul_Avio_Uskrs_i_Prvi_Maj_4_nocenja_cenovnik_1401vvt.pdf", 
        "Rim_Avio_Prvi_Maj_3_nocenja_cenovnik_1401vvt.pdf"
    ]
    
    for doc_name in test_documents:
        print(f"\n📄 DOKUMENT: {doc_name}")
        print("-" * 40)
        
        detailed_content = detail_service.get_detailed_content(doc_name, max_chunks=2)
        
        if "error" not in detailed_content:
            print(f"✅ Status: Uspešno dohvaćen")
            print(f"📊 Sadržaj: {detailed_content['content_length']} karaktera")
            print(f"🧩 Chunks: {detailed_content['total_chunks']}")
            
            structured = detailed_content['structured_content']
            print(f"💰 Cene: {structured.get('prices', [])[:3]}...")  # Show first 3
            print(f"📅 Datumi: {structured.get('dates', [])[:3]}...")  # Show first 3
            print(f"🏨 Sadržaji: {structured.get('amenities', [])[:3]}...")  # Show first 3
            
            # Test specific questions
            specific_questions = [
                "Koji su datumi polaska?",
                "Koliko košta?", 
                "Šta je uključeno u program?"
            ]
            
            for question in specific_questions:
                has_relevant_info = detail_service.should_fetch_detailed_content(question, "")
                print(f"❓ '{question}' -> Treba detaljno: {has_relevant_info}")
                
        else:
            print(f"❌ Greška: {detailed_content['error']}")

async def test_conversation_scenario():
    """
    Test realnog razgovora scenarija
    """
    print("\n💬 TESTIRANJE: Razgovor Scenario")
    print("=" * 50)
    
    # Simulate conversation flow
    conversation = [
        "Imaš li nešto za Amsterdam u maju?",
        "Koliko košta Amsterdam putovanje?",  # General question
        "Koji su konkretni datumi polaska?",  # Specific question - should trigger detailed retrieval
        "Šta je uključeno u program?",        # Another specific question
        "Da li ima spa u hotelu?"             # Very specific amenity question
    ]
    
    vector_service = VectorService()
    detail_service = DocumentDetailService(vector_service)
    
    print("Simulacija razgovora:")
    for i, user_message in enumerate(conversation, 1):
        print(f"\n{i}. Korisnik: '{user_message}'")
        
        # Check if this query needs detailed content
        needs_detailed = detail_service.should_fetch_detailed_content(user_message, "")
        
        if needs_detailed:
            print("   🔍 TRIGGERED: Potreban detaljni sadržaj")
            
            # Find relevant documents
            search_query = SearchQuery(query=user_message, limit=2)
            search_results = vector_service.search(search_query)
            
            if search_results.results:
                doc_name = search_results.results[0].metadata.source_file
                detailed_content = detail_service.get_detailed_content(doc_name)
                
                if "error" not in detailed_content:
                    structured = detailed_content['structured_content']
                    print(f"   📄 Dokument: {doc_name}")
                    print(f"   💡 Dostupni detalji: {detailed_content['content_length']} chars")
                    print(f"   🎯 Relevantne cene: {structured.get('prices', [])[:2]}")
                    print(f"   🎯 Relevantni datumi: {structured.get('dates', [])[:2]}")
                    print("   ✅ AI može sada dati specifičan odgovor!")
                else:
                    print("   ❌ Greška pri dohvatanju detalja")
            else:
                print("   ❌ Nema pronađenih dokumenata")
        else:
            print("   📋 STANDARD: Koristi osnovni pristup")

async def main():
    """Run all detailed content tests"""
    print("🚀 TESTIRANJE DETALJNOG SADRŽAJA")
    print("=" * 80)
    
    tests = [
        test_detailed_content_vs_standard,
        test_specific_document_queries,
        test_conversation_scenario
    ]
    
    for test_func in tests:
        try:
            await test_func()
            print(f"✅ {test_func.__name__} PROŠAO")
        except Exception as e:
            print(f"❌ {test_func.__name__} NEUSPEŠAN: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "🔹" * 80 + "\n")
    
    print("✅ SVI TESTOVI ZAVRŠENI!")

if __name__ == "__main__":
    asyncio.run(main()) 