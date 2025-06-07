import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import pytest


@pytest.mark.api
class TestAPIPerformance:
    """Test API performance and response times."""
    
    def test_health_check_performance(self, api_client, performance_threshold):
        """Test health check endpoint performance."""
        start_time = time.time()
        response = api_client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < performance_threshold["fast_endpoints"], f"Health check took {response_time:.3f}s, expected < {performance_threshold['fast_endpoints']}s"
    
    def test_onboarding_sections_performance(self, api_client, performance_threshold):
        """Test onboarding sections endpoint performance."""
        start_time = time.time()
        response = api_client.get("/v1/onboarding/sections")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < performance_threshold["fast_endpoints"], f"Onboarding sections took {response_time:.3f}s, expected < {performance_threshold['fast_endpoints']}s"
    
    def test_activities_list_performance(self, api_client, performance_threshold):
        """Test activities list endpoint performance."""
        start_time = time.time()
        response = api_client.get("/v1/activities/")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < performance_threshold["fast_endpoints"], f"Activities list took {response_time:.3f}s, expected < {performance_threshold['fast_endpoints']}s"
    
    def test_food_database_search_performance(self, api_client, performance_threshold):
        """Test food database search endpoint performance."""
        search_data = {
            "query": "chicken",
            "limit": 10
        }
        
        start_time = time.time()
        response = api_client.post("/v1/food-database/search", json=search_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < performance_threshold["medium_endpoints"], f"Food search took {response_time:.3f}s, expected < {performance_threshold['medium_endpoints']}s"
    
    def test_macros_calculation_performance(self, api_client, performance_threshold, valid_onboarding_data):
        """Test macros calculation endpoint performance."""
        start_time = time.time()
        response = api_client.post("/v1/macros/calculate", json=valid_onboarding_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 201
        assert response_time < performance_threshold["medium_endpoints"], f"Macros calculation took {response_time:.3f}s, expected < {performance_threshold['medium_endpoints']}s"


@pytest.mark.api
class TestConcurrentRequests:
    """Test API behavior under concurrent load."""
    
    def test_concurrent_health_checks(self, base_url):
        """Test multiple concurrent health check requests."""
        def make_request():
            with httpx.Client(base_url=base_url, timeout=30.0) as client:
                start_time = time.time()
                response = client.get("/health")
                end_time = time.time()
                return {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200
                }
        
        # Run 10 concurrent requests
        num_requests = 10
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all requests succeeded
        success_count = sum(1 for result in results if result["success"])
        assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded"
        
        # Check response times
        response_times = [result["response_time"] for result in results]
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 1.0, f"Average response time {avg_response_time:.3f}s too high"
        assert max_response_time < 2.0, f"Max response time {max_response_time:.3f}s too high"
    
    def test_concurrent_onboarding_requests(self, base_url):
        """Test multiple concurrent onboarding section requests."""
        def make_request():
            with httpx.Client(base_url=base_url, timeout=30.0) as client:
                start_time = time.time()
                response = client.get("/v1/onboarding/sections")
                end_time = time.time()
                return {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200,
                    "data_size": len(response.content)
                }
        
        # Run 5 concurrent requests
        num_requests = 5
        with ThreadPoolExecutor(max_workers=num_requests) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all requests succeeded
        success_count = sum(1 for result in results if result["success"])
        assert success_count == num_requests, f"Only {success_count}/{num_requests} requests succeeded"
        
        # Verify consistent response sizes (same data)
        data_sizes = [result["data_size"] for result in results]
        assert len(set(data_sizes)) == 1, "Response sizes should be consistent across requests"
    
    def test_concurrent_food_searches(self, base_url):
        """Test multiple concurrent food search requests."""
        search_queries = ["chicken", "rice", "broccoli", "salmon", "oatmeal"]
        
        def make_search_request(query):
            with httpx.Client(base_url=base_url, timeout=30.0) as client:
                search_data = {"query": query, "limit": 5}
                start_time = time.time()
                response = client.post("/v1/food-database/search", json=search_data)
                end_time = time.time()
                return {
                    "query": query,
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "success": response.status_code == 200,
                    "results_count": len(response.json().get("results", [])) if response.status_code == 200 else 0
                }
        
        # Run concurrent searches
        with ThreadPoolExecutor(max_workers=len(search_queries)) as executor:
            futures = [executor.submit(make_search_request, query) for query in search_queries]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify all requests succeeded
        success_count = sum(1 for result in results if result["success"])
        assert success_count == len(search_queries), f"Only {success_count}/{len(search_queries)} searches succeeded"
        
        # Verify response times are reasonable
        response_times = [result["response_time"] for result in results]
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 2.0, f"Average search time {avg_response_time:.3f}s too high"


@pytest.mark.api
class TestResponseTimeConsistency:
    """Test API response time consistency across multiple calls."""
    
    def test_health_check_consistency(self, api_client):
        """Test health check response time consistency."""
        response_times = []
        num_calls = 20
        
        for _ in range(num_calls):
            start_time = time.time()
            response = api_client.get("/health")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.1)
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        
        # Assert reasonable consistency
        assert avg_time < 0.5, f"Average response time {avg_time:.3f}s too high"
        assert std_dev < 0.2, f"Response time standard deviation {std_dev:.3f}s too high (inconsistent)"
        assert max_time < 1.0, f"Max response time {max_time:.3f}s too high"
        
        # Log performance metrics for analysis
        print(f"\nHealth Check Performance Metrics:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")
        print(f"  Std Dev: {std_dev:.3f}s")
    
    def test_food_database_list_consistency(self, api_client):
        """Test food database list response time consistency."""
        response_times = []
        num_calls = 10
        
        for _ in range(num_calls):
            start_time = time.time()
            response = api_client.get("/v1/food-database/", params={"page_size": 10})
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
            
            time.sleep(0.1)
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times)
        
        # Assert reasonable consistency
        assert avg_time < 1.0, f"Average response time {avg_time:.3f}s too high"
        assert std_dev < 0.3, f"Response time standard deviation {std_dev:.3f}s too high"


@pytest.mark.api 
class TestMemoryAndResourceUsage:
    """Test API resource usage patterns."""
    
    def test_large_response_handling(self, api_client):
        """Test handling of endpoints that return large responses."""
        # Test onboarding sections (relatively large response)
        response = api_client.get("/v1/onboarding/sections")
        assert response.status_code == 200
        
        data = response.json()
        # Verify the response is substantial but not excessive
        assert len(str(data)) > 1000, "Response should be substantial"
        assert len(str(data)) < 100000, "Response should not be excessive"
    
    def test_pagination_performance_scaling(self, api_client):
        """Test that pagination performance scales reasonably."""
        page_sizes = [5, 10, 20, 50]
        response_times = []
        
        for page_size in page_sizes:
            start_time = time.time()
            response = api_client.get("/v1/food-database/", params={"page_size": page_size})
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
            
            # Verify we get the expected number of items (up to available items)
            data = response.json()
            assert len(data["foods"]) <= page_size
        
        # Response time shouldn't increase dramatically with page size
        # (since we're using mock data, this is more about API structure)
        assert all(time < 1.0 for time in response_times), "All pagination requests should be fast"


@pytest.mark.api
@pytest.mark.integration
class TestEndToEndPerformance:
    """Test end-to-end user flow performance."""
    
    def test_complete_user_flow_performance(self, api_client, valid_onboarding_data, valid_food_data):
        """Test performance of a complete user workflow."""
        total_start_time = time.time()
        
        # Step 1: Get onboarding sections
        step1_start = time.time()
        response = api_client.get("/v1/onboarding/sections")
        step1_time = time.time() - step1_start
        assert response.status_code == 200
        
        # Step 2: Calculate macros
        step2_start = time.time()
        response = api_client.post("/v1/macros/calculate", json=valid_onboarding_data)
        step2_time = time.time() - step2_start
        assert response.status_code == 201
        
        # Step 3: Search foods
        step3_start = time.time()
        search_data = {"query": "chicken", "limit": 5}
        response = api_client.post("/v1/food-database/search", json=search_data)
        step3_time = time.time() - step3_start
        assert response.status_code == 200
        
        # Step 4: Add food to database
        step4_start = time.time()
        response = api_client.post("/v1/food-database/", json=valid_food_data)
        step4_time = time.time() - step4_start
        assert response.status_code == 201
        
        # Step 5: Get activities
        step5_start = time.time()
        response = api_client.get("/v1/activities/")
        step5_time = time.time() - step5_start
        assert response.status_code == 200
        
        total_time = time.time() - total_start_time
        
        # Assert individual step performance
        assert step1_time < 1.0, f"Onboarding sections took {step1_time:.3f}s"
        assert step2_time < 2.0, f"Macro calculation took {step2_time:.3f}s"
        assert step3_time < 2.0, f"Food search took {step3_time:.3f}s"
        assert step4_time < 1.0, f"Food creation took {step4_time:.3f}s"
        assert step5_time < 1.0, f"Activities list took {step5_time:.3f}s"
        
        # Assert total workflow performance
        assert total_time < 7.0, f"Complete workflow took {total_time:.3f}s, should be under 7s"
        
        # Log performance breakdown
        print(f"\nEnd-to-End Performance Breakdown:")
        print(f"  1. Onboarding sections: {step1_time:.3f}s")
        print(f"  2. Macro calculation: {step2_time:.3f}s")
        print(f"  3. Food search: {step3_time:.3f}s")
        print(f"  4. Food creation: {step4_time:.3f}s")
        print(f"  5. Activities list: {step5_time:.3f}s")
        print(f"  Total workflow time: {total_time:.3f}s")


if __name__ == "__main__":
    # Run performance tests with: python -m pytest tests/test_performance.py -v -m "api"
    pytest.main([__file__, "-v", "-m", "api"]) 