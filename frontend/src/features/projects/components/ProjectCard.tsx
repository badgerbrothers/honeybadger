import { Card } from '@/components/ui/Card';
import { Project } from '@/lib/types';
import Link from 'next/link';

interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link href={`/projects/${project.id}`}>
      <Card className="hover:shadow-lg transition-shadow cursor-pointer">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          {project.name}
        </h3>
        <p className="text-gray-600 text-sm mb-4">
          {project.description || 'No description'}
        </p>
        <p className="text-xs text-gray-400">
          Created {new Date(project.created_at).toLocaleDateString()}
        </p>
      </Card>
    </Link>
  );
}
