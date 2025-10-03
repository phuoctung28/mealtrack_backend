"""
Unit tests for PineconeNutritionService.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.infra.services.pinecone_service import (
    PineconeNutritionService,
    NutritionData,
    get_pinecone_service
)


@pytest.mark.unit
class TestNutritionData:
    """Test NutritionData dataclass."""
    
    def test_scale_to_doubles_nutrition(self):
        """Test scaling nutrition to double the serving size."""
        # Arrange
        nutrition = NutritionData(
            calories=100,
            protein=10,
            fat=5,
            carbs=15,
            fiber=2,
            sugar=5,
            sodium=200,
            serving_size_g=100
        )
        
        # Act
        scaled = nutrition.scale_to(200)
        
        # Assert
        assert scaled.calories == 200
        assert scaled.protein == 20
        assert scaled.fat == 10
        assert scaled.carbs == 30
        assert scaled.fiber == 4
        assert scaled.sugar == 10
        assert scaled.sodium == 400
        assert scaled.serving_size_g == 200
    
    def test_scale_to_half_nutrition(self):
        """Test scaling nutrition to half the serving size."""
        # Arrange
        nutrition = NutritionData(
            calories=200,
            protein=20,
            fat=10,
            carbs=30,
            serving_size_g=100
        )
        
        # Act
        scaled = nutrition.scale_to(50)
        
        # Assert
        assert scaled.calories == 100
        assert scaled.protein == 10
        assert scaled.fat == 5
        assert scaled.carbs == 15
        assert scaled.serving_size_g == 50
    
    def test_scale_to_zero_serving_size_returns_same(self):
        """Test scaling when serving size is zero returns unchanged."""
        # Arrange
        nutrition = NutritionData(
            calories=100,
            protein=10,
            serving_size_g=0
        )
        
        # Act
        scaled = nutrition.scale_to(200)
        
        # Assert
        assert scaled.calories == 100
        assert scaled.protein == 10
        assert scaled.serving_size_g == 0


@pytest.mark.unit
class TestPineconeNutritionService:
    """Test PineconeNutritionService."""
    
    @patch('src.infra.services.pinecone_service.Pinecone')
    @patch('src.infra.services.pinecone_service.SentenceTransformer')
    def test_init_connects_to_indexes(self, mock_transformer, mock_pinecone):
        """Test service initialization connects to Pinecone indexes."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_ingredients_index = Mock()
        mock_usda_index = Mock()
        mock_usda_index.describe_index_stats.return_value = {'total_vector_count': 456000}
        
        def mock_index(name):
            if name == "ingredients":
                return mock_ingredients_index
            elif name == "usda":
                return mock_usda_index
        
        mock_pc.Index.side_effect = mock_index
        
        # Act
        service = PineconeNutritionService(pinecone_api_key="test-key")
        
        # Assert
        mock_pinecone.assert_called_once_with(api_key="test-key")
        assert service.ingredients_index == mock_ingredients_index
        assert service.usda_index == mock_usda_index
    
    @patch('src.infra.services.pinecone_service.Pinecone')
    @patch('src.infra.services.pinecone_service.SentenceTransformer')
    def test_search_ingredient_finds_in_ingredients_index(self, mock_transformer, mock_pinecone):
        """Test searching finds ingredient in ingredients index."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_ingredients_index = Mock()
        mock_usda_index = Mock()
        
        # Mock query result from ingredients index
        mock_ingredients_index.query.return_value = {
            'matches': [{
                'score': 0.85,
                'metadata': {
                    'name': 'Chicken Breast',
                    'calories': 165,
                    'protein': 31,
                    'fat': 3.6,
                    'carbs': 0,
                    'fiber': 0,
                    'sugar': 0,
                    'sodium': 74,
                    'serving_size': '100g'
                }
            }]
        }
        
        def mock_index(name):
            if name == "ingredients":
                return mock_ingredients_index
            elif name == "usda":
                return mock_usda_index
        
        mock_pc.Index.side_effect = mock_index
        mock_usda_index.describe_index_stats.return_value = {'total_vector_count': 456000}
        
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock(tolist=lambda: [0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_encoder
        
        service = PineconeNutritionService(pinecone_api_key="test-key")
        
        # Act
        result = service.search_ingredient("chicken breast")
        
        # Assert
        assert result is not None
        assert result['name'] == 'Chicken Breast'
        assert result['calories'] == 165
        assert result['protein'] == 31
        assert result['score'] == 0.85
    
    @patch('src.infra.services.pinecone_service.Pinecone')
    @patch('src.infra.services.pinecone_service.SentenceTransformer')
    def test_search_ingredient_tries_usda_if_low_score(self, mock_transformer, mock_pinecone):
        """Test searching falls back to USDA index if ingredients score is low."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_ingredients_index = Mock()
        mock_usda_index = Mock()
        
        # Mock low score from ingredients index
        mock_ingredients_index.query.return_value = {
            'matches': [{
                'score': 0.40,
                'metadata': {'name': 'Low Match', 'calories': 100}
            }]
        }
        
        # Mock better score from USDA index
        mock_usda_index.query.return_value = {
            'matches': [{
                'score': 0.75,
                'metadata': {
                    'name': 'Better Match',
                    'calories': 150,
                    'protein': 20,
                    'fat': 5,
                    'carbs': 10,
                    'fiber': 2,
                    'sugar': 3,
                    'sodium': 100
                }
            }]
        }
        
        def mock_index(name):
            if name == "ingredients":
                return mock_ingredients_index
            elif name == "usda":
                return mock_usda_index
        
        mock_pc.Index.side_effect = mock_index
        mock_usda_index.describe_index_stats.return_value = {'total_vector_count': 456000}
        
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock(tolist=lambda: [0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_encoder
        
        service = PineconeNutritionService(pinecone_api_key="test-key")
        
        # Act
        result = service.search_ingredient("exotic ingredient")
        
        # Assert
        assert result is not None
        assert result['name'] == 'Better Match'
        assert result['score'] == 0.75
        # Both indexes should have been queried
        mock_ingredients_index.query.assert_called_once()
        mock_usda_index.query.assert_called_once()
    
    @patch('src.infra.services.pinecone_service.Pinecone')
    @patch('src.infra.services.pinecone_service.SentenceTransformer')
    def test_search_ingredient_returns_none_if_no_match(self, mock_transformer, mock_pinecone):
        """Test searching returns None when no match found."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_ingredients_index = Mock()
        mock_usda_index = Mock()
        
        # Mock no matches
        mock_ingredients_index.query.return_value = {'matches': []}
        mock_usda_index.query.return_value = {'matches': []}
        
        def mock_index(name):
            if name == "ingredients":
                return mock_ingredients_index
            elif name == "usda":
                return mock_usda_index
        
        mock_pc.Index.side_effect = mock_index
        mock_usda_index.describe_index_stats.return_value = {'total_vector_count': 456000}
        
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock(tolist=lambda: [0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_encoder
        
        service = PineconeNutritionService(pinecone_api_key="test-key")
        
        # Act
        result = service.search_ingredient("unknown food")
        
        # Assert
        assert result is None
    
    @patch('src.infra.services.pinecone_service.Pinecone')
    @patch('src.infra.services.pinecone_service.SentenceTransformer')
    def test_convert_to_grams(self, mock_transformer, mock_pinecone):
        """Test unit conversion to grams."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_pc.Index.side_effect = Exception("Not needed")
        
        service = PineconeNutritionService(pinecone_api_key="test-key")
        service.ingredients_index = Mock()  # Bypass init
        service.usda_index = Mock()
        
        # Act & Assert
        assert service.convert_to_grams(100, "g") == 100
        assert service.convert_to_grams(1, "kg") == 1000
        assert service.convert_to_grams(1, "oz") == 28.35
        assert service.convert_to_grams(1, "cup") == 240
        assert service.convert_to_grams(1, "tbsp") == 15
        assert service.convert_to_grams(1, "tsp") == 5
    
    @patch('src.infra.services.pinecone_service.Pinecone')
    @patch('src.infra.services.pinecone_service.SentenceTransformer')
    def test_get_scaled_nutrition(self, mock_transformer, mock_pinecone):
        """Test getting scaled nutrition for ingredient."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_ingredients_index = Mock()
        
        # Mock search result
        mock_ingredients_index.query.return_value = {
            'matches': [{
                'score': 0.85,
                'metadata': {
                    'name': 'Rice',
                    'calories': 130,
                    'protein': 2.7,
                    'fat': 0.3,
                    'carbs': 28,
                    'fiber': 0.4,
                    'sugar': 0.1,
                    'sodium': 1
                }
            }]
        }
        
        mock_pc.Index.return_value = mock_ingredients_index
        
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock(tolist=lambda: [0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_encoder
        
        service = PineconeNutritionService(pinecone_api_key="test-key")
        
        # Act - request 200g of rice
        result = service.get_scaled_nutrition("rice", 200, "g")
        
        # Assert
        assert result is not None
        assert result.calories == 260  # 130 * 2
        assert result.protein == 5.4   # 2.7 * 2
        assert result.carbs == 56      # 28 * 2
        assert result.serving_size_g == 200
    
    @patch('src.infra.services.pinecone_service.Pinecone')
    @patch('src.infra.services.pinecone_service.SentenceTransformer')
    def test_calculate_total_nutrition(self, mock_transformer, mock_pinecone):
        """Test calculating total nutrition from multiple ingredients."""
        # Arrange
        mock_pc = Mock()
        mock_pinecone.return_value = mock_pc
        mock_ingredients_index = Mock()
        
        # Mock different ingredients
        def mock_query(vector, top_k, include_metadata):
            # Return different results based on call count
            if not hasattr(mock_query, 'call_count'):
                mock_query.call_count = 0
            
            mock_query.call_count += 1
            
            if mock_query.call_count == 1:  # chicken
                return {
                    'matches': [{
                        'score': 0.85,
                        'metadata': {
                            'name': 'Chicken Breast',
                            'calories': 165,
                            'protein': 31,
                            'fat': 3.6,
                            'carbs': 0,
                            'fiber': 0,
                            'sugar': 0,
                            'sodium': 74
                        }
                    }]
                }
            elif mock_query.call_count == 2:  # rice
                return {
                    'matches': [{
                        'score': 0.85,
                        'metadata': {
                            'name': 'Rice',
                            'calories': 130,
                            'protein': 2.7,
                            'fat': 0.3,
                            'carbs': 28,
                            'fiber': 0.4,
                            'sugar': 0.1,
                            'sodium': 1
                        }
                    }]
                }
        
        mock_ingredients_index.query.side_effect = mock_query
        mock_pc.Index.return_value = mock_ingredients_index
        
        mock_encoder = Mock()
        mock_encoder.encode.return_value = Mock(tolist=lambda: [0.1, 0.2, 0.3])
        mock_transformer.return_value = mock_encoder
        
        service = PineconeNutritionService(pinecone_api_key="test-key")
        
        # Act - 200g chicken + 150g rice
        ingredients = [
            {'name': 'chicken breast', 'quantity': 200, 'unit': 'g'},
            {'name': 'rice', 'quantity': 150, 'unit': 'g'}
        ]
        result = service.calculate_total_nutrition(ingredients)
        
        # Assert
        # Chicken: 165*2=330, Rice: 130*1.5=195, Total: 525
        assert result.calories == 525
        # Chicken: 31*2=62, Rice: 2.7*1.5=4.05, Total: 66.05
        assert result.protein == pytest.approx(66.05, 0.1)
        # Chicken: 0*2=0, Rice: 28*1.5=42, Total: 42
        assert result.carbs == 42
        # Total weight: 200+150=350
        assert result.serving_size_g == 350


@pytest.mark.unit
class TestGetPineconeService:
    """Test get_pinecone_service singleton."""
    
    @patch('src.infra.services.pinecone_service.PineconeNutritionService')
    def test_returns_singleton_instance(self, mock_service_class):
        """Test that get_pinecone_service returns the same instance."""
        # Arrange
        import src.infra.services.pinecone_service as service_module
        service_module._pinecone_service_instance = None  # Reset singleton
        
        mock_instance = Mock()
        mock_service_class.return_value = mock_instance
        
        # Act
        instance1 = get_pinecone_service()
        instance2 = get_pinecone_service()
        
        # Assert
        assert instance1 is instance2
        mock_service_class.assert_called_once()  # Only initialized once
        
        # Cleanup
        service_module._pinecone_service_instance = None
