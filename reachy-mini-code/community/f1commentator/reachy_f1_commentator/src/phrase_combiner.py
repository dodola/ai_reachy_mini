"""
Phrase Combiner for Enhanced Commentary System.

This module provides phrase combination functionality that populates templates
with context data and constructs natural compound sentences.

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6
"""

import logging
import re
from typing import Optional

from reachy_f1_commentator.src.config import Config
from reachy_f1_commentator.src.enhanced_models import ContextData, Template
from reachy_f1_commentator.src.placeholder_resolver import PlaceholderResolver


logger = logging.getLogger(__name__)


class PhraseCombiner:
    """
    Constructs natural commentary by populating templates with context data.
    
    Handles placeholder resolution, value formatting, output validation,
    and sentence length enforcement to generate grammatically correct
    compound sentences.
    
    Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6
    """
    
    def __init__(self, config: Config, placeholder_resolver: PlaceholderResolver):
        """
        Initialize phrase combiner.
        
        Args:
            config: System configuration with max_sentence_length
            placeholder_resolver: Resolver for template placeholders
        """
        self.config = config
        self.placeholder_resolver = placeholder_resolver
        self.max_sentence_length = config.max_sentence_length
        logger.debug(f"PhraseCombiner initialized with max_sentence_length={self.max_sentence_length}")
    
    def generate_commentary(self, template: Template, context: ContextData) -> str:
        """
        Generate final commentary text from template and context.
        
        This is the main entry point that orchestrates the entire phrase
        combination process:
        1. Resolve all placeholders in the template
        2. Format values appropriately
        3. Validate output has no remaining placeholders
        4. Truncate if needed to enforce max sentence length
        
        Args:
            template: Selected template with placeholder text
            context: Enriched context data for the event
            
        Returns:
            Final commentary text ready for speech synthesis
            
        Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6
        """
        logger.debug(f"Generating commentary from template {template.template_id}")
        
        # Step 1: Resolve all placeholders
        text = self._resolve_placeholders(template.template_text, context)
        
        # Step 2: Clean up any formatting issues
        text = self._clean_text(text)
        
        # Step 3: Validate output
        if not self._validate_output(text):
            logger.warning(f"Generated commentary failed validation: {text}")
            # Try to clean up any remaining placeholders
            text = self._remove_unresolved_placeholders(text)
        
        # Step 4: Truncate if needed
        text = self._truncate_if_needed(text)
        
        logger.debug(f"Generated commentary: {text}")
        return text
    
    def _resolve_placeholders(self, template_text: str, context: ContextData) -> str:
        """
        Replace all placeholders with actual values from context.
        
        Finds all placeholders in the format {placeholder_name} and replaces
        them with resolved values. If a placeholder cannot be resolved,
        it is left in place for later handling.
        
        Args:
            template_text: Template text with placeholders
            context: Context data containing values
            
        Returns:
            Text with placeholders replaced by values
            
        Validates: Requirements 4.2, 4.3
        """
        # Find all placeholders in the template
        placeholder_pattern = r'\{([^}]+)\}'
        placeholders = re.findall(placeholder_pattern, template_text)
        
        result = template_text
        
        # Resolve each placeholder
        for placeholder in placeholders:
            value = self.placeholder_resolver.resolve(placeholder, context)
            
            if value is not None:
                # Replace the placeholder with the resolved value
                result = result.replace(f"{{{placeholder}}}", str(value))
                logger.debug(f"Resolved placeholder '{placeholder}' to '{value}'")
            else:
                logger.debug(f"Could not resolve placeholder '{placeholder}'")
        
        return result
    
    def _format_values(self, placeholder: str, value: any) -> str:
        """
        Apply formatting rules to values.
        
        This method is primarily handled by the PlaceholderResolver,
        but provides an additional layer for any post-processing needed.
        
        Args:
            placeholder: Placeholder name
            value: Raw value to format
            
        Returns:
            Formatted value string
            
        Validates: Requirements 4.2, 4.3
        """
        # Most formatting is handled by PlaceholderResolver
        # This method is here for any additional formatting needs
        return str(value)
    
    def _validate_output(self, text: str) -> bool:
        """
        Validate that output has no remaining placeholders and is grammatical.
        
        Checks for:
        - No unresolved placeholders (text in curly braces)
        - Text is not empty
        - Text has reasonable structure (starts with capital, ends with period)
        
        Args:
            text: Generated commentary text
            
        Returns:
            True if output is valid, False otherwise
            
        Validates: Requirements 4.4
        """
        if not text or not text.strip():
            logger.warning("Generated text is empty")
            return False
        
        # Check for unresolved placeholders
        if '{' in text and '}' in text:
            # Find any remaining placeholders
            remaining = re.findall(r'\{([^}]+)\}', text)
            if remaining:
                logger.warning(f"Unresolved placeholders found: {remaining}")
                return False
        
        # Check for basic grammatical structure
        text = text.strip()
        
        # Should start with a capital letter or number
        if not text[0].isupper() and not text[0].isdigit():
            logger.debug(f"Text does not start with capital: {text[:20]}")
            # This is a warning, not a failure
        
        # Should end with punctuation (period, exclamation, question mark)
        if not text[-1] in '.!?':
            logger.debug(f"Text does not end with punctuation: {text[-20:]}")
            # This is a warning, not a failure
        
        return True
    
    def _truncate_if_needed(self, text: str) -> str:
        """
        Truncate sentence if it exceeds max length.
        
        Enforces the maximum sentence length (default 40 words) to maintain
        clarity and prevent overly long commentary. Truncates at sentence
        boundaries when possible to maintain grammatical correctness.
        
        Args:
            text: Generated commentary text
            
        Returns:
            Truncated text if needed, original text otherwise
            
        Validates: Requirements 4.6
        """
        # Count words
        words = text.split()
        word_count = len(words)
        
        if word_count <= self.max_sentence_length:
            return text
        
        logger.debug(f"Text exceeds max length ({word_count} > {self.max_sentence_length}), truncating")
        
        # Truncate to max length
        truncated_words = words[:self.max_sentence_length]
        truncated_text = ' '.join(truncated_words)
        
        # Try to end at a natural boundary (comma, semicolon, or period)
        # Work backwards from the end to find a good break point
        for i in range(len(truncated_text) - 1, max(0, len(truncated_text) - 50), -1):
            if truncated_text[i] in '.,;':
                # Found a natural break point
                truncated_text = truncated_text[:i+1]
                break
        
        # Ensure it ends with a period if it doesn't already end with punctuation
        if truncated_text and truncated_text[-1] not in '.!?':
            truncated_text += '.'
        
        logger.debug(f"Truncated from {word_count} to {len(truncated_text.split())} words")
        return truncated_text
    
    def _clean_text(self, text: str) -> str:
        """
        Clean up formatting issues in generated text.
        
        Handles:
        - Multiple consecutive spaces
        - Spaces before punctuation
        - Missing spaces after punctuation
        - Empty optional sections (double spaces, orphaned commas)
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove multiple consecutive spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # Ensure space after punctuation (except at end)
        text = re.sub(r'([.,;:!?])([A-Za-z])', r'\1 \2', text)
        
        # Clean up orphaned commas and conjunctions from unresolved optional placeholders
        # e.g., "Hamilton overtakes , and moves into P1" -> "Hamilton overtakes and moves into P1"
        text = re.sub(r'\s*,\s*,\s*', ', ', text)  # Double commas
        text = re.sub(r'\s*,\s+and\s+', ' and ', text)  # Orphaned comma before 'and'
        text = re.sub(r'\s*,\s+with\s+', ' with ', text)  # Orphaned comma before 'with'
        text = re.sub(r'\s*,\s+while\s+', ' while ', text)  # Orphaned comma before 'while'
        text = re.sub(r'\s*,\s+as\s+', ' as ', text)  # Orphaned comma before 'as'
        
        # Clean up double spaces that might have been created
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _remove_unresolved_placeholders(self, text: str) -> str:
        """
        Remove any unresolved placeholders from text.
        
        This is a fallback for when placeholders couldn't be resolved.
        Removes the placeholder and cleans up any resulting formatting issues.
        
        Args:
            text: Text with potential unresolved placeholders
            
        Returns:
            Text with placeholders removed
        """
        # Remove all remaining placeholders
        text = re.sub(r'\{[^}]+\}', '', text)
        
        # Clean up any resulting formatting issues
        text = self._clean_text(text)
        
        return text

