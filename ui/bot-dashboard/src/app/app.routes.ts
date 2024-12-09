import { Routes } from '@angular/router';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { DetailsComponent } from './features/details/details.component';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'home',
  },
  {
    path: 'home',
    component: DashboardComponent,
    children: [
      {
        path: 'child',
        loadComponent: () =>
          import('./features/dashboard/child/child.component').then(
            (m) => m.ChildComponent
          ),
      },
    ],
  },
  {
    path: 'details',
    component: DetailsComponent,
  },
];
