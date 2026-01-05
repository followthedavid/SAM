// Template Library - Pre-built Code Templates (Option 3)
//
// Provides code templates that can be filled in with minimal AI:
// - React components, hooks, contexts
// - API endpoints (Express, FastAPI, Actix)
// - Test suites (Jest, Pytest, Rust tests)
// - Rust structs, enums, traits
// - TypeScript interfaces and types
// - Configuration files (Docker, CI/CD)
//
// The LLM only fills in specific details, not generating from scratch

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// =============================================================================
// TEMPLATE DEFINITIONS
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeTemplate {
    pub id: String,
    pub name: String,
    pub description: String,
    pub language: String,
    pub category: TemplateCategory,
    pub template: String,
    pub placeholders: Vec<Placeholder>,
    pub example_output: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum TemplateCategory {
    ReactComponent,
    ReactHook,
    VueComponent,
    ApiEndpoint,
    Test,
    RustStruct,
    RustEnum,
    RustTrait,
    RustImpl,
    TypeScriptInterface,
    TypeScriptType,
    PythonClass,
    PythonFunction,
    GoStruct,
    GoHandler,
    SqlMigration,
    GraphQL,
    Configuration,
    Docker,
    CiCd,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Placeholder {
    pub name: String,
    pub description: String,
    pub default: Option<String>,
    pub required: bool,
    pub ai_fill: bool,  // Whether AI should fill this
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemplateResult {
    pub code: String,
    pub placeholders_filled: HashMap<String, String>,
    pub ai_used: bool,
    pub warnings: Vec<String>,
}

// =============================================================================
// TEMPLATE LIBRARY
// =============================================================================

pub struct TemplateLibrary {
    templates: HashMap<String, CodeTemplate>,
}

impl TemplateLibrary {
    pub fn new() -> Self {
        let mut lib = Self {
            templates: HashMap::new(),
        };
        lib.load_builtin_templates();
        lib
    }

    pub fn get(&self, id: &str) -> Option<&CodeTemplate> {
        self.templates.get(id)
    }

    pub fn list(&self) -> Vec<&CodeTemplate> {
        self.templates.values().collect()
    }

    pub fn list_by_category(&self, category: TemplateCategory) -> Vec<&CodeTemplate> {
        self.templates.values()
            .filter(|t| t.category == category)
            .collect()
    }

    pub fn search(&self, query: &str) -> Vec<&CodeTemplate> {
        let lower = query.to_lowercase();
        self.templates.values()
            .filter(|t| {
                t.name.to_lowercase().contains(&lower) ||
                t.description.to_lowercase().contains(&lower) ||
                t.id.to_lowercase().contains(&lower)
            })
            .collect()
    }

    /// Fill a template with provided values (no AI)
    pub fn fill(&self, template_id: &str, values: &HashMap<String, String>) -> Result<TemplateResult, String> {
        let template = self.templates.get(template_id)
            .ok_or_else(|| format!("Template '{}' not found", template_id))?;

        let mut code = template.template.clone();
        let mut filled = HashMap::new();
        let mut warnings = Vec::new();

        for placeholder in &template.placeholders {
            let key = format!("{{{{{}}}}}",  placeholder.name);

            if let Some(value) = values.get(&placeholder.name) {
                code = code.replace(&key, value);
                filled.insert(placeholder.name.clone(), value.clone());
            } else if let Some(default) = &placeholder.default {
                code = code.replace(&key, default);
                filled.insert(placeholder.name.clone(), default.clone());
                warnings.push(format!("Using default for '{}': {}", placeholder.name, default));
            } else if placeholder.required {
                return Err(format!("Required placeholder '{}' not provided", placeholder.name));
            }
        }

        Ok(TemplateResult {
            code,
            placeholders_filled: filled,
            ai_used: false,
            warnings,
        })
    }

    /// Generate prompt for AI to fill remaining placeholders
    pub fn generate_fill_prompt(&self, template_id: &str, context: &str, partial_values: &HashMap<String, String>) -> Result<String, String> {
        let template = self.templates.get(template_id)
            .ok_or_else(|| format!("Template '{}' not found", template_id))?;

        let unfilled: Vec<&Placeholder> = template.placeholders.iter()
            .filter(|p| p.ai_fill && !partial_values.contains_key(&p.name))
            .collect();

        if unfilled.is_empty() {
            return Err("All AI placeholders already filled".to_string());
        }

        let mut prompt = format!(
            "Fill in the following placeholders for a {} template.\n\nContext: {}\n\nPlaceholders to fill:\n",
            template.name, context
        );

        for p in &unfilled {
            prompt.push_str(&format!("- {}: {}\n", p.name, p.description));
        }

        prompt.push_str("\nRespond with JSON like: {\"placeholder_name\": \"value\", ...}\n");
        prompt.push_str("Keep values concise and appropriate for code.\n");

        Ok(prompt)
    }

    // =========================================================================
    // BUILTIN TEMPLATES
    // =========================================================================

    fn load_builtin_templates(&mut self) {
        // React Component
        self.add_template(CodeTemplate {
            id: "react_component".to_string(),
            name: "React Functional Component".to_string(),
            description: "A React functional component with TypeScript".to_string(),
            language: "tsx".to_string(),
            category: TemplateCategory::ReactComponent,
            template: r#"import React from 'react';

interface {{COMPONENT_NAME}}Props {
  {{PROPS}}
}

export const {{COMPONENT_NAME}}: React.FC<{{COMPONENT_NAME}}Props> = ({
  {{DESTRUCTURED_PROPS}}
}) => {
  {{HOOKS}}

  {{HANDLERS}}

  return (
    <div className="{{CSS_CLASS}}">
      {{JSX_CONTENT}}
    </div>
  );
};

export default {{COMPONENT_NAME}};
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "COMPONENT_NAME".to_string(), description: "Name of the component (PascalCase)".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "PROPS".to_string(), description: "TypeScript interface properties".to_string(), default: Some("// Add props here".to_string()), required: false, ai_fill: true },
                Placeholder { name: "DESTRUCTURED_PROPS".to_string(), description: "Destructured props in function signature".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "HOOKS".to_string(), description: "React hooks (useState, useEffect, etc.)".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "HANDLERS".to_string(), description: "Event handler functions".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "CSS_CLASS".to_string(), description: "CSS class name".to_string(), default: None, required: false, ai_fill: false },
                Placeholder { name: "JSX_CONTENT".to_string(), description: "JSX content to render".to_string(), default: Some("{/* Content */}".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // React Hook
        self.add_template(CodeTemplate {
            id: "react_hook".to_string(),
            name: "React Custom Hook".to_string(),
            description: "A custom React hook with TypeScript".to_string(),
            language: "ts".to_string(),
            category: TemplateCategory::ReactHook,
            template: r#"import { useState, useEffect, useCallback } from 'react';

interface {{HOOK_NAME}}Options {
  {{OPTIONS}}
}

interface {{HOOK_NAME}}Return {
  {{RETURN_TYPE}}
}

export function {{HOOK_NAME}}(options: {{HOOK_NAME}}Options = {}): {{HOOK_NAME}}Return {
  {{STATE}}

  {{EFFECTS}}

  {{CALLBACKS}}

  return {
    {{RETURN_VALUES}}
  };
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "HOOK_NAME".to_string(), description: "Name of the hook (use prefix)".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "OPTIONS".to_string(), description: "Options interface properties".to_string(), default: Some("// options".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RETURN_TYPE".to_string(), description: "Return type interface".to_string(), default: Some("// return type".to_string()), required: false, ai_fill: true },
                Placeholder { name: "STATE".to_string(), description: "useState declarations".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "EFFECTS".to_string(), description: "useEffect blocks".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "CALLBACKS".to_string(), description: "useCallback functions".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RETURN_VALUES".to_string(), description: "Values to return".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Express API Endpoint
        self.add_template(CodeTemplate {
            id: "api_endpoint_express".to_string(),
            name: "Express API Endpoint".to_string(),
            description: "A REST API endpoint with Express.js".to_string(),
            language: "ts".to_string(),
            category: TemplateCategory::ApiEndpoint,
            template: r#"import { Router, Request, Response, NextFunction } from 'express';
import { {{SERVICE}} } from '../services/{{SERVICE_FILE}}';

const router = Router();

// {{DESCRIPTION}}
router.{{METHOD}}('{{PATH}}', async (req: Request, res: Response, next: NextFunction) => {
  try {
    {{VALIDATION}}

    {{LOGIC}}

    res.status({{STATUS_CODE}}).json({
      success: true,
      {{RESPONSE}}
    });
  } catch (error) {
    next(error);
  }
});

export default router;
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "SERVICE".to_string(), description: "Service class/function to import".to_string(), default: Some("service".to_string()), required: false, ai_fill: false },
                Placeholder { name: "SERVICE_FILE".to_string(), description: "Service file name".to_string(), default: Some("service".to_string()), required: false, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Endpoint description".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "METHOD".to_string(), description: "HTTP method (get/post/put/delete)".to_string(), default: Some("get".to_string()), required: true, ai_fill: false },
                Placeholder { name: "PATH".to_string(), description: "Route path".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "VALIDATION".to_string(), description: "Input validation code".to_string(), default: Some("// Validate input".to_string()), required: false, ai_fill: true },
                Placeholder { name: "LOGIC".to_string(), description: "Business logic".to_string(), default: Some("// Process request".to_string()), required: false, ai_fill: true },
                Placeholder { name: "STATUS_CODE".to_string(), description: "HTTP status code".to_string(), default: Some("200".to_string()), required: false, ai_fill: false },
                Placeholder { name: "RESPONSE".to_string(), description: "Response data".to_string(), default: Some("data: {}".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // FastAPI Endpoint
        self.add_template(CodeTemplate {
            id: "api_endpoint_fastapi".to_string(),
            name: "FastAPI Endpoint".to_string(),
            description: "A REST API endpoint with FastAPI".to_string(),
            language: "python".to_string(),
            category: TemplateCategory::ApiEndpoint,
            template: r#"from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

class {{REQUEST_MODEL}}(BaseModel):
    {{REQUEST_FIELDS}}

class {{RESPONSE_MODEL}}(BaseModel):
    {{RESPONSE_FIELDS}}

@router.{{METHOD}}("{{PATH}}", response_model={{RESPONSE_MODEL}})
async def {{FUNCTION_NAME}}(
    {{PARAMS}}
) -> {{RESPONSE_MODEL}}:
    """{{DESCRIPTION}}"""
    {{LOGIC}}

    return {{RESPONSE_MODEL}}(
        {{RETURN_VALUES}}
    )
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "REQUEST_MODEL".to_string(), description: "Request Pydantic model name".to_string(), default: Some("RequestModel".to_string()), required: false, ai_fill: false },
                Placeholder { name: "REQUEST_FIELDS".to_string(), description: "Request model fields".to_string(), default: Some("pass".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RESPONSE_MODEL".to_string(), description: "Response Pydantic model name".to_string(), default: Some("ResponseModel".to_string()), required: false, ai_fill: false },
                Placeholder { name: "RESPONSE_FIELDS".to_string(), description: "Response model fields".to_string(), default: Some("success: bool".to_string()), required: false, ai_fill: true },
                Placeholder { name: "METHOD".to_string(), description: "HTTP method".to_string(), default: Some("get".to_string()), required: true, ai_fill: false },
                Placeholder { name: "PATH".to_string(), description: "Route path".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "FUNCTION_NAME".to_string(), description: "Function name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "PARAMS".to_string(), description: "Function parameters".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Endpoint docstring".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "LOGIC".to_string(), description: "Business logic".to_string(), default: Some("pass".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RETURN_VALUES".to_string(), description: "Return values".to_string(), default: Some("success=True".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Rust Struct
        self.add_template(CodeTemplate {
            id: "rust_struct".to_string(),
            name: "Rust Struct".to_string(),
            description: "A Rust struct with common derives".to_string(),
            language: "rust".to_string(),
            category: TemplateCategory::RustStruct,
            template: r#"use serde::{Deserialize, Serialize};

/// {{DESCRIPTION}}
#[derive(Debug, Clone, {{DERIVES}})]
pub struct {{STRUCT_NAME}} {
    {{FIELDS}}
}

impl {{STRUCT_NAME}} {
    pub fn new({{CONSTRUCTOR_PARAMS}}) -> Self {
        Self {
            {{CONSTRUCTOR_BODY}}
        }
    }

    {{METHODS}}
}

impl Default for {{STRUCT_NAME}} {
    fn default() -> Self {
        Self {
            {{DEFAULT_VALUES}}
        }
    }
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "STRUCT_NAME".to_string(), description: "Name of the struct".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Struct documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DERIVES".to_string(), description: "Additional derives".to_string(), default: Some("Serialize, Deserialize".to_string()), required: false, ai_fill: false },
                Placeholder { name: "FIELDS".to_string(), description: "Struct fields".to_string(), default: Some("// Add fields".to_string()), required: false, ai_fill: true },
                Placeholder { name: "CONSTRUCTOR_PARAMS".to_string(), description: "Constructor parameters".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "CONSTRUCTOR_BODY".to_string(), description: "Constructor body".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "METHODS".to_string(), description: "Additional methods".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "DEFAULT_VALUES".to_string(), description: "Default trait values".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Rust Enum
        self.add_template(CodeTemplate {
            id: "rust_enum".to_string(),
            name: "Rust Enum".to_string(),
            description: "A Rust enum with serialization".to_string(),
            language: "rust".to_string(),
            category: TemplateCategory::RustEnum,
            template: r#"use serde::{Deserialize, Serialize};

/// {{DESCRIPTION}}
#[derive(Debug, Clone, Copy, PartialEq, Eq, {{DERIVES}})]
pub enum {{ENUM_NAME}} {
    {{VARIANTS}}
}

impl {{ENUM_NAME}} {
    pub fn as_str(&self) -> &'static str {
        match self {
            {{AS_STR_ARMS}}
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            {{FROM_STR_ARMS}}
            _ => None,
        }
    }

    {{METHODS}}
}

impl std::fmt::Display for {{ENUM_NAME}} {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "ENUM_NAME".to_string(), description: "Name of the enum".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Enum documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DERIVES".to_string(), description: "Additional derives".to_string(), default: Some("Serialize, Deserialize".to_string()), required: false, ai_fill: false },
                Placeholder { name: "VARIANTS".to_string(), description: "Enum variants".to_string(), default: Some("// Add variants".to_string()), required: false, ai_fill: true },
                Placeholder { name: "AS_STR_ARMS".to_string(), description: "Match arms for as_str".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "FROM_STR_ARMS".to_string(), description: "Match arms for from_str".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "METHODS".to_string(), description: "Additional methods".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Jest Test
        self.add_template(CodeTemplate {
            id: "test_jest".to_string(),
            name: "Jest Test Suite".to_string(),
            description: "A Jest test suite with TypeScript".to_string(),
            language: "ts".to_string(),
            category: TemplateCategory::Test,
            template: r#"import { {{IMPORTS}} } from '{{IMPORT_PATH}}';

describe('{{DESCRIBE}}', () => {
  {{SETUP}}

  beforeEach(() => {
    {{BEFORE_EACH}}
  });

  afterEach(() => {
    {{AFTER_EACH}}
  });

  {{TEST_CASES}}
});
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "IMPORTS".to_string(), description: "Items to import".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "IMPORT_PATH".to_string(), description: "Import path".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIBE".to_string(), description: "Test suite description".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "SETUP".to_string(), description: "Test setup (mocks, fixtures)".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "BEFORE_EACH".to_string(), description: "beforeEach hook code".to_string(), default: Some("jest.clearAllMocks();".to_string()), required: false, ai_fill: false },
                Placeholder { name: "AFTER_EACH".to_string(), description: "afterEach hook code".to_string(), default: Some("".to_string()), required: false, ai_fill: false },
                Placeholder { name: "TEST_CASES".to_string(), description: "Test cases".to_string(), default: Some("it('should work', () => {\n    expect(true).toBe(true);\n  });".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Rust Test
        self.add_template(CodeTemplate {
            id: "test_rust".to_string(),
            name: "Rust Test Module".to_string(),
            description: "A Rust test module".to_string(),
            language: "rust".to_string(),
            category: TemplateCategory::Test,
            template: r#"#[cfg(test)]
mod tests {
    use super::*;

    {{FIXTURES}}

    {{TEST_CASES}}
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "FIXTURES".to_string(), description: "Test fixtures and helpers".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "TEST_CASES".to_string(), description: "Test functions".to_string(), default: Some("#[test]\n    fn test_example() {\n        assert!(true);\n    }".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Pytest Test
        self.add_template(CodeTemplate {
            id: "test_pytest".to_string(),
            name: "Pytest Test Module".to_string(),
            description: "A Pytest test module".to_string(),
            language: "python".to_string(),
            category: TemplateCategory::Test,
            template: r#"import pytest
from {{IMPORT_PATH}} import {{IMPORTS}}

{{FIXTURES}}

class Test{{CLASS_NAME}}:
    """{{DESCRIPTION}}"""

    {{SETUP}}

    {{TEST_METHODS}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "IMPORT_PATH".to_string(), description: "Import path".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "IMPORTS".to_string(), description: "Items to import".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "CLASS_NAME".to_string(), description: "Test class name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Test class docstring".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "FIXTURES".to_string(), description: "Pytest fixtures".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "SETUP".to_string(), description: "Setup method".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "TEST_METHODS".to_string(), description: "Test methods".to_string(), default: Some("def test_example(self):\n        assert True".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // TypeScript Interface
        self.add_template(CodeTemplate {
            id: "ts_interface".to_string(),
            name: "TypeScript Interface".to_string(),
            description: "A TypeScript interface".to_string(),
            language: "ts".to_string(),
            category: TemplateCategory::TypeScriptInterface,
            template: r#"/**
 * {{DESCRIPTION}}
 */
export interface {{INTERFACE_NAME}} {{EXTENDS}} {
  {{PROPERTIES}}
}

{{RELATED_TYPES}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "INTERFACE_NAME".to_string(), description: "Interface name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Interface documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "EXTENDS".to_string(), description: "Extends clause".to_string(), default: Some("".to_string()), required: false, ai_fill: false },
                Placeholder { name: "PROPERTIES".to_string(), description: "Interface properties".to_string(), default: Some("// Add properties".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RELATED_TYPES".to_string(), description: "Related type aliases".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Python Class
        self.add_template(CodeTemplate {
            id: "python_class".to_string(),
            name: "Python Class".to_string(),
            description: "A Python class with dataclass or attrs".to_string(),
            language: "python".to_string(),
            category: TemplateCategory::PythonClass,
            template: r#"from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class {{CLASS_NAME}}:
    """{{DESCRIPTION}}"""

    {{FIELDS}}

    def __post_init__(self):
        {{POST_INIT}}

    {{METHODS}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "CLASS_NAME".to_string(), description: "Class name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Class docstring".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "FIELDS".to_string(), description: "Dataclass fields".to_string(), default: Some("pass".to_string()), required: false, ai_fill: true },
                Placeholder { name: "POST_INIT".to_string(), description: "__post_init__ body".to_string(), default: Some("pass".to_string()), required: false, ai_fill: true },
                Placeholder { name: "METHODS".to_string(), description: "Class methods".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Dockerfile
        self.add_template(CodeTemplate {
            id: "dockerfile".to_string(),
            name: "Dockerfile".to_string(),
            description: "A multi-stage Dockerfile".to_string(),
            language: "dockerfile".to_string(),
            category: TemplateCategory::Docker,
            template: r#"# Build stage
FROM {{BUILD_IMAGE}} AS builder
WORKDIR /app
{{BUILD_DEPS}}
COPY . .
RUN {{BUILD_CMD}}

# Production stage
FROM {{PROD_IMAGE}}
WORKDIR /app
{{PROD_DEPS}}
COPY --from=builder {{BUILD_ARTIFACTS}}
{{ENV_VARS}}
EXPOSE {{PORT}}
CMD {{CMD}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "BUILD_IMAGE".to_string(), description: "Build stage base image".to_string(), default: Some("node:20-alpine".to_string()), required: false, ai_fill: false },
                Placeholder { name: "BUILD_DEPS".to_string(), description: "Build dependencies".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "BUILD_CMD".to_string(), description: "Build command".to_string(), default: Some("npm ci && npm run build".to_string()), required: false, ai_fill: false },
                Placeholder { name: "PROD_IMAGE".to_string(), description: "Production base image".to_string(), default: Some("node:20-alpine".to_string()), required: false, ai_fill: false },
                Placeholder { name: "PROD_DEPS".to_string(), description: "Production dependencies".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "BUILD_ARTIFACTS".to_string(), description: "Artifacts to copy from builder".to_string(), default: Some("/app/dist ./dist".to_string()), required: false, ai_fill: false },
                Placeholder { name: "ENV_VARS".to_string(), description: "Environment variables".to_string(), default: Some("ENV NODE_ENV=production".to_string()), required: false, ai_fill: false },
                Placeholder { name: "PORT".to_string(), description: "Exposed port".to_string(), default: Some("3000".to_string()), required: false, ai_fill: false },
                Placeholder { name: "CMD".to_string(), description: "Startup command".to_string(), default: Some("[\"node\", \"dist/index.js\"]".to_string()), required: false, ai_fill: false },
            ],
            example_output: None,
        });

        // GitHub Actions
        self.add_template(CodeTemplate {
            id: "github_actions".to_string(),
            name: "GitHub Actions Workflow".to_string(),
            description: "A GitHub Actions CI/CD workflow".to_string(),
            language: "yaml".to_string(),
            category: TemplateCategory::CiCd,
            template: r#"name: {{WORKFLOW_NAME}}

on:
  {{TRIGGERS}}

env:
  {{ENV_VARS}}

jobs:
  {{JOBS}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "WORKFLOW_NAME".to_string(), description: "Workflow name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "TRIGGERS".to_string(), description: "Workflow triggers".to_string(), default: Some("push:\n    branches: [main]\n  pull_request:\n    branches: [main]".to_string()), required: false, ai_fill: false },
                Placeholder { name: "ENV_VARS".to_string(), description: "Environment variables".to_string(), default: Some("CI: true".to_string()), required: false, ai_fill: false },
                Placeholder { name: "JOBS".to_string(), description: "Job definitions".to_string(), default: Some("build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Actix Web Endpoint
        self.add_template(CodeTemplate {
            id: "api_endpoint_actix".to_string(),
            name: "Actix Web Endpoint".to_string(),
            description: "A REST API endpoint with Actix Web".to_string(),
            language: "rust".to_string(),
            category: TemplateCategory::ApiEndpoint,
            template: r#"use actix_web::{web, HttpResponse, Result};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct {{REQUEST_NAME}} {
    {{REQUEST_FIELDS}}
}

#[derive(Debug, Serialize)]
pub struct {{RESPONSE_NAME}} {
    {{RESPONSE_FIELDS}}
}

/// {{DESCRIPTION}}
pub async fn {{HANDLER_NAME}}(
    {{PARAMS}}
) -> Result<HttpResponse> {
    {{LOGIC}}

    Ok(HttpResponse::Ok().json({{RESPONSE_NAME}} {
        {{RESPONSE_VALUES}}
    }))
}

pub fn configure(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::resource("{{PATH}}")
            .route(web::{{METHOD}}().to({{HANDLER_NAME}}))
    );
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "REQUEST_NAME".to_string(), description: "Request struct name".to_string(), default: Some("RequestBody".to_string()), required: false, ai_fill: false },
                Placeholder { name: "REQUEST_FIELDS".to_string(), description: "Request struct fields".to_string(), default: Some("// fields".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RESPONSE_NAME".to_string(), description: "Response struct name".to_string(), default: Some("ResponseBody".to_string()), required: false, ai_fill: false },
                Placeholder { name: "RESPONSE_FIELDS".to_string(), description: "Response struct fields".to_string(), default: Some("success: bool,".to_string()), required: false, ai_fill: true },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Handler documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "HANDLER_NAME".to_string(), description: "Handler function name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "PARAMS".to_string(), description: "Handler parameters".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "LOGIC".to_string(), description: "Handler logic".to_string(), default: Some("// Process request".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RESPONSE_VALUES".to_string(), description: "Response field values".to_string(), default: Some("success: true,".to_string()), required: false, ai_fill: true },
                Placeholder { name: "PATH".to_string(), description: "Route path".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "METHOD".to_string(), description: "HTTP method".to_string(), default: Some("get".to_string()), required: true, ai_fill: false },
            ],
            example_output: None,
        });

        // =================================================================
        // NEW TEMPLATES - Extended Language Coverage
        // =================================================================

        // Vue 3 Component (Composition API)
        self.add_template(CodeTemplate {
            id: "vue_component".to_string(),
            name: "Vue 3 Component".to_string(),
            description: "A Vue 3 component with Composition API and TypeScript".to_string(),
            language: "vue".to_string(),
            category: TemplateCategory::VueComponent,
            template: r#"<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
{{IMPORTS}}

interface Props {
  {{PROPS}}
}

const props = defineProps<Props>()
const emit = defineEmits<{
  {{EMITS}}
}>()

{{STATE}}

{{COMPUTED}}

{{METHODS}}

onMounted(() => {
  {{ON_MOUNTED}}
})
</script>

<template>
  <div class="{{CSS_CLASS}}">
    {{TEMPLATE}}
  </div>
</template>

<style scoped>
.{{CSS_CLASS}} {
  {{STYLES}}
}
</style>
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "IMPORTS".to_string(), description: "Additional imports".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "PROPS".to_string(), description: "Props interface".to_string(), default: Some("// Add props".to_string()), required: false, ai_fill: true },
                Placeholder { name: "EMITS".to_string(), description: "Emit definitions".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "STATE".to_string(), description: "Reactive state (ref, reactive)".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "COMPUTED".to_string(), description: "Computed properties".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "METHODS".to_string(), description: "Methods".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "ON_MOUNTED".to_string(), description: "onMounted hook code".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "CSS_CLASS".to_string(), description: "Root CSS class".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "TEMPLATE".to_string(), description: "Template content".to_string(), default: Some("<!-- Content -->".to_string()), required: false, ai_fill: true },
                Placeholder { name: "STYLES".to_string(), description: "CSS styles".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Go Struct
        self.add_template(CodeTemplate {
            id: "go_struct".to_string(),
            name: "Go Struct".to_string(),
            description: "A Go struct with JSON tags and methods".to_string(),
            language: "go".to_string(),
            category: TemplateCategory::GoStruct,
            template: r#"package {{PACKAGE}}

import (
	{{IMPORTS}}
)

// {{DESCRIPTION}}
type {{STRUCT_NAME}} struct {
	{{FIELDS}}
}

// New{{STRUCT_NAME}} creates a new {{STRUCT_NAME}} instance
func New{{STRUCT_NAME}}({{CONSTRUCTOR_PARAMS}}) *{{STRUCT_NAME}} {
	return &{{STRUCT_NAME}}{
		{{CONSTRUCTOR_BODY}}
	}
}

{{METHODS}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "PACKAGE".to_string(), description: "Package name".to_string(), default: Some("main".to_string()), required: true, ai_fill: false },
                Placeholder { name: "IMPORTS".to_string(), description: "Import statements".to_string(), default: Some("\"encoding/json\"".to_string()), required: false, ai_fill: true },
                Placeholder { name: "STRUCT_NAME".to_string(), description: "Struct name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Struct documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "FIELDS".to_string(), description: "Struct fields with tags".to_string(), default: Some("ID string `json:\"id\"`".to_string()), required: false, ai_fill: true },
                Placeholder { name: "CONSTRUCTOR_PARAMS".to_string(), description: "Constructor parameters".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "CONSTRUCTOR_BODY".to_string(), description: "Constructor body".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "METHODS".to_string(), description: "Struct methods".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Go HTTP Handler
        self.add_template(CodeTemplate {
            id: "go_handler".to_string(),
            name: "Go HTTP Handler".to_string(),
            description: "A Go HTTP handler with standard library".to_string(),
            language: "go".to_string(),
            category: TemplateCategory::GoHandler,
            template: r#"package {{PACKAGE}}

import (
	"encoding/json"
	"net/http"
	{{IMPORTS}}
)

type {{REQUEST_NAME}} struct {
	{{REQUEST_FIELDS}}
}

type {{RESPONSE_NAME}} struct {
	Success bool   `json:"success"`
	{{RESPONSE_FIELDS}}
}

// {{DESCRIPTION}}
func {{HANDLER_NAME}}(w http.ResponseWriter, r *http.Request) {
	{{VALIDATION}}

	{{LOGIC}}

	response := {{RESPONSE_NAME}}{
		Success: true,
		{{RESPONSE_VALUES}}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "PACKAGE".to_string(), description: "Package name".to_string(), default: Some("handlers".to_string()), required: true, ai_fill: false },
                Placeholder { name: "IMPORTS".to_string(), description: "Additional imports".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "REQUEST_NAME".to_string(), description: "Request struct name".to_string(), default: Some("Request".to_string()), required: false, ai_fill: false },
                Placeholder { name: "REQUEST_FIELDS".to_string(), description: "Request fields".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RESPONSE_NAME".to_string(), description: "Response struct name".to_string(), default: Some("Response".to_string()), required: false, ai_fill: false },
                Placeholder { name: "RESPONSE_FIELDS".to_string(), description: "Response fields".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "HANDLER_NAME".to_string(), description: "Handler function name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Handler documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "VALIDATION".to_string(), description: "Request validation".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "LOGIC".to_string(), description: "Handler logic".to_string(), default: Some("// Process request".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RESPONSE_VALUES".to_string(), description: "Response field values".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Go Test
        self.add_template(CodeTemplate {
            id: "test_go".to_string(),
            name: "Go Test".to_string(),
            description: "A Go test file with table-driven tests".to_string(),
            language: "go".to_string(),
            category: TemplateCategory::Test,
            template: r#"package {{PACKAGE}}

import (
	"testing"
	{{IMPORTS}}
)

func Test{{FUNCTION_NAME}}(t *testing.T) {
	{{FIXTURES}}

	tests := []struct {
		name    string
		{{TEST_FIELDS}}
		want    {{WANT_TYPE}}
		wantErr bool
	}{
		{{TEST_CASES}}
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			{{TEST_BODY}}
		})
	}
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "PACKAGE".to_string(), description: "Package name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "IMPORTS".to_string(), description: "Additional imports".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "FUNCTION_NAME".to_string(), description: "Function being tested".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "FIXTURES".to_string(), description: "Test fixtures".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "TEST_FIELDS".to_string(), description: "Test case fields".to_string(), default: Some("input string".to_string()), required: false, ai_fill: true },
                Placeholder { name: "WANT_TYPE".to_string(), description: "Expected return type".to_string(), default: Some("string".to_string()), required: false, ai_fill: false },
                Placeholder { name: "TEST_CASES".to_string(), description: "Test case definitions".to_string(), default: Some("{name: \"example\", input: \"\", want: \"\", wantErr: false},".to_string()), required: false, ai_fill: true },
                Placeholder { name: "TEST_BODY".to_string(), description: "Test body".to_string(), default: Some("// Arrange, Act, Assert".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Rust Trait
        self.add_template(CodeTemplate {
            id: "rust_trait".to_string(),
            name: "Rust Trait".to_string(),
            description: "A Rust trait definition".to_string(),
            language: "rust".to_string(),
            category: TemplateCategory::RustTrait,
            template: r#"/// {{DESCRIPTION}}
pub trait {{TRAIT_NAME}} {{BOUNDS}} {
    {{ASSOCIATED_TYPES}}

    {{REQUIRED_METHODS}}

    {{PROVIDED_METHODS}}
}

{{IMPLEMENTATIONS}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "TRAIT_NAME".to_string(), description: "Trait name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Trait documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "BOUNDS".to_string(), description: "Supertrait bounds".to_string(), default: Some("".to_string()), required: false, ai_fill: false },
                Placeholder { name: "ASSOCIATED_TYPES".to_string(), description: "Associated type definitions".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "REQUIRED_METHODS".to_string(), description: "Required method signatures".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "PROVIDED_METHODS".to_string(), description: "Default method implementations".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "IMPLEMENTATIONS".to_string(), description: "Example implementations".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // TypeScript Type (Zod schema compatible)
        self.add_template(CodeTemplate {
            id: "ts_type".to_string(),
            name: "TypeScript Type with Zod".to_string(),
            description: "A TypeScript type with Zod schema validation".to_string(),
            language: "ts".to_string(),
            category: TemplateCategory::TypeScriptType,
            template: r#"import { z } from 'zod';

/**
 * {{DESCRIPTION}}
 */
export const {{SCHEMA_NAME}}Schema = z.object({
  {{SCHEMA_FIELDS}}
});

export type {{TYPE_NAME}} = z.infer<typeof {{SCHEMA_NAME}}Schema>;

{{RELATED_SCHEMAS}}

// Validation helper
export function validate{{TYPE_NAME}}(data: unknown): {{TYPE_NAME}} {
  return {{SCHEMA_NAME}}Schema.parse(data);
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "TYPE_NAME".to_string(), description: "Type name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "SCHEMA_NAME".to_string(), description: "Schema variable name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Type documentation".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "SCHEMA_FIELDS".to_string(), description: "Zod schema fields".to_string(), default: Some("id: z.string(),".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RELATED_SCHEMAS".to_string(), description: "Related schemas (arrays, optionals)".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Python Function
        self.add_template(CodeTemplate {
            id: "python_function".to_string(),
            name: "Python Function".to_string(),
            description: "A Python function with type hints and docstring".to_string(),
            language: "python".to_string(),
            category: TemplateCategory::PythonFunction,
            template: r#"from typing import {{TYPING_IMPORTS}}
{{IMPORTS}}


def {{FUNCTION_NAME}}({{PARAMS}}) -> {{RETURN_TYPE}}:
    """{{DESCRIPTION}}

    Args:
        {{ARGS_DOC}}

    Returns:
        {{RETURNS_DOC}}

    Raises:
        {{RAISES_DOC}}
    """
    {{BODY}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "FUNCTION_NAME".to_string(), description: "Function name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "TYPING_IMPORTS".to_string(), description: "Typing module imports".to_string(), default: Some("Optional, List, Dict".to_string()), required: false, ai_fill: false },
                Placeholder { name: "IMPORTS".to_string(), description: "Additional imports".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "PARAMS".to_string(), description: "Function parameters".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RETURN_TYPE".to_string(), description: "Return type".to_string(), default: Some("None".to_string()), required: false, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Function description".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "ARGS_DOC".to_string(), description: "Args documentation".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RETURNS_DOC".to_string(), description: "Returns documentation".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RAISES_DOC".to_string(), description: "Raises documentation".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "BODY".to_string(), description: "Function body".to_string(), default: Some("pass".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // SQL Migration
        self.add_template(CodeTemplate {
            id: "sql_migration".to_string(),
            name: "SQL Migration".to_string(),
            description: "A SQL migration with up and down".to_string(),
            language: "sql".to_string(),
            category: TemplateCategory::SqlMigration,
            template: r#"-- Migration: {{MIGRATION_NAME}}
-- Created at: {{CREATED_AT}}

-- Up Migration
{{UP_MIGRATION}}

-- Down Migration
{{DOWN_MIGRATION}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "MIGRATION_NAME".to_string(), description: "Migration name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "CREATED_AT".to_string(), description: "Creation timestamp".to_string(), default: Some("NOW()".to_string()), required: false, ai_fill: false },
                Placeholder { name: "UP_MIGRATION".to_string(), description: "Up migration SQL".to_string(), default: Some("-- Add your up migration here".to_string()), required: false, ai_fill: true },
                Placeholder { name: "DOWN_MIGRATION".to_string(), description: "Down migration SQL".to_string(), default: Some("-- Add your down migration here".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // GraphQL Schema
        self.add_template(CodeTemplate {
            id: "graphql_schema".to_string(),
            name: "GraphQL Schema".to_string(),
            description: "A GraphQL type definition".to_string(),
            language: "graphql".to_string(),
            category: TemplateCategory::GraphQL,
            template: r#""""
{{DESCRIPTION}}
"""
type {{TYPE_NAME}} {{IMPLEMENTS}} {
  {{FIELDS}}
}

{{INPUT_TYPE}}

{{QUERIES}}

{{MUTATIONS}}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "TYPE_NAME".to_string(), description: "Type name".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "DESCRIPTION".to_string(), description: "Type description".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "IMPLEMENTS".to_string(), description: "Implemented interfaces".to_string(), default: Some("".to_string()), required: false, ai_fill: false },
                Placeholder { name: "FIELDS".to_string(), description: "Type fields".to_string(), default: Some("id: ID!".to_string()), required: false, ai_fill: true },
                Placeholder { name: "INPUT_TYPE".to_string(), description: "Input type definition".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "QUERIES".to_string(), description: "Query definitions".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "MUTATIONS".to_string(), description: "Mutation definitions".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // React Context
        self.add_template(CodeTemplate {
            id: "react_context".to_string(),
            name: "React Context".to_string(),
            description: "A React context with provider and hooks".to_string(),
            language: "tsx".to_string(),
            category: TemplateCategory::ReactComponent,
            template: r#"import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';

interface {{CONTEXT_NAME}}State {
  {{STATE_INTERFACE}}
}

interface {{CONTEXT_NAME}}Actions {
  {{ACTIONS_INTERFACE}}
}

interface {{CONTEXT_NAME}}Value extends {{CONTEXT_NAME}}State, {{CONTEXT_NAME}}Actions {}

const {{CONTEXT_NAME}}Context = createContext<{{CONTEXT_NAME}}Value | undefined>(undefined);

interface {{CONTEXT_NAME}}ProviderProps {
  children: React.ReactNode;
  {{PROVIDER_PROPS}}
}

export function {{CONTEXT_NAME}}Provider({ children, {{DESTRUCTURED_PROPS}} }: {{CONTEXT_NAME}}ProviderProps) {
  {{STATE}}

  {{ACTIONS}}

  const value = useMemo(() => ({
    {{VALUE_OBJECT}}
  }), [{{DEPENDENCIES}}]);

  return (
    <{{CONTEXT_NAME}}Context.Provider value={value}>
      {children}
    </{{CONTEXT_NAME}}Context.Provider>
  );
}

export function use{{CONTEXT_NAME}}() {
  const context = useContext({{CONTEXT_NAME}}Context);
  if (context === undefined) {
    throw new Error('use{{CONTEXT_NAME}} must be used within a {{CONTEXT_NAME}}Provider');
  }
  return context;
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "CONTEXT_NAME".to_string(), description: "Context name (PascalCase)".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "STATE_INTERFACE".to_string(), description: "State interface properties".to_string(), default: Some("// Add state properties".to_string()), required: false, ai_fill: true },
                Placeholder { name: "ACTIONS_INTERFACE".to_string(), description: "Actions interface".to_string(), default: Some("// Add action methods".to_string()), required: false, ai_fill: true },
                Placeholder { name: "PROVIDER_PROPS".to_string(), description: "Provider props".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "DESTRUCTURED_PROPS".to_string(), description: "Destructured props".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "STATE".to_string(), description: "useState declarations".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "ACTIONS".to_string(), description: "Action implementations".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "VALUE_OBJECT".to_string(), description: "Context value object".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "DEPENDENCIES".to_string(), description: "useMemo dependencies".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });

        // Next.js API Route
        self.add_template(CodeTemplate {
            id: "nextjs_api".to_string(),
            name: "Next.js API Route".to_string(),
            description: "A Next.js API route handler".to_string(),
            language: "ts".to_string(),
            category: TemplateCategory::ApiEndpoint,
            template: r#"import type { NextApiRequest, NextApiResponse } from 'next';
{{IMPORTS}}

interface RequestBody {
  {{REQUEST_BODY}}
}

interface ResponseData {
  {{RESPONSE_DATA}}
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData | { error: string }>
) {
  if (req.method !== '{{METHOD}}') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    {{VALIDATION}}

    {{LOGIC}}

    return res.status(200).json({
      {{RESPONSE_VALUES}}
    });
  } catch (error) {
    console.error('{{ENDPOINT_NAME}} error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
"#.to_string(),
            placeholders: vec![
                Placeholder { name: "IMPORTS".to_string(), description: "Additional imports".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "REQUEST_BODY".to_string(), description: "Request body interface".to_string(), default: Some("".to_string()), required: false, ai_fill: true },
                Placeholder { name: "RESPONSE_DATA".to_string(), description: "Response data interface".to_string(), default: Some("success: boolean;".to_string()), required: false, ai_fill: true },
                Placeholder { name: "METHOD".to_string(), description: "HTTP method".to_string(), default: Some("POST".to_string()), required: true, ai_fill: false },
                Placeholder { name: "VALIDATION".to_string(), description: "Request validation".to_string(), default: Some("const body = req.body as RequestBody;".to_string()), required: false, ai_fill: true },
                Placeholder { name: "LOGIC".to_string(), description: "Handler logic".to_string(), default: Some("// Process request".to_string()), required: false, ai_fill: true },
                Placeholder { name: "ENDPOINT_NAME".to_string(), description: "Endpoint name for logging".to_string(), default: None, required: true, ai_fill: false },
                Placeholder { name: "RESPONSE_VALUES".to_string(), description: "Response values".to_string(), default: Some("success: true".to_string()), required: false, ai_fill: true },
            ],
            example_output: None,
        });
    }

    fn add_template(&mut self, template: CodeTemplate) {
        self.templates.insert(template.id.clone(), template);
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    pub static ref TEMPLATE_LIBRARY: std::sync::Mutex<TemplateLibrary> =
        std::sync::Mutex::new(TemplateLibrary::new());
}

pub fn templates() -> std::sync::MutexGuard<'static, TemplateLibrary> {
    TEMPLATE_LIBRARY.lock().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_template_fill() {
        let lib = TemplateLibrary::new();
        let mut values = HashMap::new();
        values.insert("STRUCT_NAME".to_string(), "MyStruct".to_string());
        values.insert("DESCRIPTION".to_string(), "A test struct".to_string());

        let result = lib.fill("rust_struct", &values).unwrap();
        assert!(result.code.contains("pub struct MyStruct"));
        assert!(!result.ai_used);
    }

    #[test]
    fn test_template_search() {
        let lib = TemplateLibrary::new();
        let results = lib.search("react");
        assert!(results.len() >= 2); // component and hook
    }

    #[test]
    fn test_template_by_category() {
        let lib = TemplateLibrary::new();
        let tests = lib.list_by_category(TemplateCategory::Test);
        assert!(tests.len() >= 2); // jest, rust, pytest
    }
}
