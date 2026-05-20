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