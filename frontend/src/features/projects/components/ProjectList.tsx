import { useProjects } from '../hooks/useProjects';
import { ProjectCard } from './ProjectCard';

export function ProjectList() {
  const { data: projects, isLoading, error } = useProjects();

  if (isLoading) {
    return <div className="text-center py-12">Loading projects...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600">
        Failed to load projects: {error.message}
      </div>
    );
  }

  if (!projects || projects.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        No projects yet. Create your first project to get started.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {projects.map((project) => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  );
}
