"""
Base mapper class for API data transformation.
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List

# Type variables for domain and DTO types
DomainModel = TypeVar('DomainModel')
RequestDTO = TypeVar('RequestDTO')
ResponseDTO = TypeVar('ResponseDTO')


class BaseMapper(ABC, Generic[DomainModel, RequestDTO, ResponseDTO]):
    """
    Abstract base class for mappers that convert between domain models and DTOs.
    
    Provides a consistent interface for data transformation between layers:
    - Request DTO → Domain Model (for incoming requests)
    - Domain Model → Response DTO (for outgoing responses)
    """
    
    @abstractmethod
    def to_domain(self, dto: RequestDTO) -> DomainModel:
        """
        Convert a request DTO to a domain model.
        
        Args:
            dto: The request DTO to convert
            
        Returns:
            The corresponding domain model
        """
        pass
    
    @abstractmethod
    def to_response_dto(self, domain: DomainModel) -> ResponseDTO:
        """
        Convert a domain model to a response DTO.
        
        Args:
            domain: The domain model to convert
            
        Returns:
            The corresponding response DTO
        """
        pass
    
    def to_domain_list(self, dtos: List[RequestDTO]) -> List[DomainModel]:
        """
        Convert a list of request DTOs to domain models.
        
        Args:
            dtos: List of request DTOs
            
        Returns:
            List of domain models
        """
        return [self.to_domain(dto) for dto in dtos]
    
    def to_response_dto_list(self, domains: List[DomainModel]) -> List[ResponseDTO]:
        """
        Convert a list of domain models to response DTOs.
        
        Args:
            domains: List of domain models
            
        Returns:
            List of response DTOs
        """
        return [self.to_response_dto(domain) for domain in domains]