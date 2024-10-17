import { Component } from '@angular/core';
import { RouterOutlet,RouterLink } from '@angular/router';
import { ChildComponent } from './child/child.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent {

}
