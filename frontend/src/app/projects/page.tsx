'use client';

import { Container } from '@/components/layout/Container';
import { ProjectList } from '@/features/projects/components/ProjectList';
import { CreateProjectForm } from '@/features/projects/components/CreateProjectForm';

export default function ProjectsPage() {
  return (
    <Container>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Projects</h1>
          <p className="text-gray-600">
            Manage your AI task execution workspaces
          </p>
        </div>

        <CreateProjectForm />

        <div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            Your Projects
          </h2>
          <ProjectList />
        </div>
      </div>
    </Container>
  );
}
