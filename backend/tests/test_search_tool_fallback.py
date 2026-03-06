
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.tools.search_tool import search_tax_regulations_tool
from datetime import datetime

@pytest.mark.asyncio
async def test_search_tool_fallback_logic():
    # Scenario: Current year is 2025.
    # 2025 Search -> Returns empty HTML (no results)
    # 2024 Search -> Returns valid HTML with results
    
    current_year = datetime.now().year
    target_year = current_year
    fallback_year = current_year - 1
    
    with patch('httpx.AsyncClient') as MockClient:
        # Mock instance
        mock_client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client_instance
        
        # We expect 2 phases of calls.
        # Phase 1: 3 calls for target_year (AEAT, BOE, SegSocial) -> All return NO results
        # Phase 2: 3 calls for fallback_year -> One returns results
        
        async def side_effect(*args, **kwargs):
            # Inspect 'data' payload to see which query is being run
            data = kwargs.get('data', {})
            query = data.get('q', '')
            
            if str(target_year) in query:
                # Simulate Empty Result for 2025
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.text = "<html><body>No results</body></html>"
                return mock_resp
            elif str(fallback_year) in query:
                # Simulate Success for 2024
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                # Use class='result__a' which is what the tool looks for (DuckDuckGo structure)
                mock_resp.text = f"""
                <html><body>
                    <div class="result">
                        <a class="result__a" href="https://www.agenciatributaria.es/normativa/{fallback_year}">
                            Normativa IRPF {fallback_year}
                        </a>
                    </div>
                </body></html>
                """
                return mock_resp
            return MagicMock(status_code=404)

        mock_client_instance.post.side_effect = side_effect
        
        # Execute Tool
        result = await search_tax_regulations_tool(
            query="IRPF",
            year=target_year,
            extract_data=False # Keep it simple, just search
        )
        
        # Assertions
        assert result['success'] is True
        assert result['year'] == fallback_year  # Should be updated to fallback
        assert len(result['results']) > 0
        assert str(fallback_year) in result['results'][0]['title']
        assert "agenciatributaria" in result['results'][0]['url']
        
        # Verify Fallback Message in Formatted Response
        # (Though exact text assertion depends on implementation, we check for presence of data)
