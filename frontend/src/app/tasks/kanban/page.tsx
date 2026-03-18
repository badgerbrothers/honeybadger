import { Container } from '@/components/layout/Container';
import { TaskKanbanBoard } from '@/features/tasks/components/TaskKanbanBoard';

export default function KanbanPage() {
  return (
    <Container>
      <div className="space-y-6 py-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Task Queue</h1>
          <p className="mt-2 text-gray-600">Manage scheduled work and run priorities in one Kanban board.</p>
        </div>
        <TaskKanbanBoard />
      </div>
    </Container>
  );
}
