export interface Category {
  id: string
  name: string
  slug: string
  icon: string
  description: string | null
  sort_order: number
  components_count: number
  registry_count: number
  community_count: number
}

export interface Component {
  id: string
  name: string
  slug: string
  category: string
  image: string
  image_source: string
  registry_url: string
  is_registry: boolean
  registry_number: string | null
  description: string | null
  version: string | null
  default_ports: Record<string, number>
  default_volumes: Record<string, string>
  default_env: Record<string, string>
  variables_schema: Record<string, unknown>
  has_registry: boolean
  build_method: string | null
}

export interface Stack {
  id: string
  name: string
  slug: string
  description: string
  is_featured: boolean
  components: StackComponent[]
}

export interface StackComponent {
  name: string
  slug: string
  is_registry: boolean
  image?: string
  registry_url?: string
}

export interface ComponentConfig {
  ports: Record<string, number>
  volumes: Record<string, string>
  env: Record<string, string>
}

// --- Registry types ---

export interface RegistryComponent {
  slug: string
  name: string
  version: string
  category: string
  description: string
  build_method: string
  provides: string[]
  has_dockerfile: boolean
  source_url: string
  community_url: string | null
}

export interface RegistryManifest {
  component: {
    slug: string
    name: string
    version: string
    category: string
    description: string
    source_url: string
    documentation_url: string
    build_method: string
    build_args: Record<string, string>
    dependencies: {
      requires: string[]
      provides: string[]
    }
    ports: Record<string, number>
    default_env: Record<string, string>
  }
}

// --- Constructor types ---

export interface ConstructorRequest {
  components: string[]
  profile: string
  configs: Record<string, Record<string, unknown>>
}

export interface ConstructorDiagnostic {
  resolved: string[]
  auto_added: { slug: string; reason: string; provides: string }[]
  profile: { slug: string; label: string; description: string } | null
  errors: string[]
}

export interface SecurityProfile {
  slug: string
  label: string
  description: string
}

// --- Security report types ---

export interface Vulnerability {
  id: string
  pkg: string
  severity: string
  title: string
  fixed: string
}

export interface TrivyReport {
  total_vulnerabilities: number
  by_severity: { CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number; UNKNOWN: number }
  vulnerabilities: Vulnerability[]
}

export interface SbomDependency {
  name: string
  version: string
  type: string
}

export interface SbomReport {
  total_components: number
  by_type: Record<string, number>
  top_dependencies: SbomDependency[]
  tools: string[]
  bom_format: string
  spec_version: string
}

export interface CosignStatus {
  signed: boolean
  public_key: string | null
  signature: string | null
}

export interface SecurityReport {
  slug: string
  profile: string
  status: 'ok' | 'error'
  errors: string[]
  sbom: SbomReport | null
  trivy: TrivyReport | null
  owasp: Record<string, unknown> | null
  cosign: CosignStatus
}
