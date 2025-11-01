"""Тест для проверки логики переиндексации."""

import pytest
from src.core.config import Settings


def test_reindex_flag_from_env():
    """Тест чтения флага переиндексации из переменной окружения."""
    # Тест с false
    settings = Settings(reindex_on_startup="false")
    assert settings.should_reindex_on_startup is False
    
    # Тест с true
    settings = Settings(reindex_on_startup="true")
    assert settings.should_reindex_on_startup is True
    
    # Тест с 1
    settings = Settings(reindex_on_startup="1")
    assert settings.should_reindex_on_startup is True
    
    # Тест с yes
    settings = Settings(reindex_on_startup="yes")
    assert settings.should_reindex_on_startup is True


def test_force_reindex_priority():
    """Тест приоритета force_reindex над reindex_on_startup."""
    # force_reindex имеет приоритет
    settings = Settings(reindex_on_startup="false")
    settings.force_reindex = True
    assert settings.should_reindex_on_startup is True
    
    # force_reindex=False, используется reindex_on_startup
    settings = Settings(reindex_on_startup="true")
    settings.force_reindex = False
    assert settings.should_reindex_on_startup is True
    
    # Оба false
    settings = Settings(reindex_on_startup="false")
    settings.force_reindex = False
    assert settings.should_reindex_on_startup is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
