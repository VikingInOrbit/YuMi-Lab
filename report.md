\documentclass[nn]{NMBU}

\usepackage{multirow}
\usepackage{float}
\usepackage{algorithm}
\usepackage[noend]{algpseudocode}
\usepackage{graphicx}

\credits{10}
\studyprogramme{Anvendt Robotikk}
\course{TEL200 Introduksjon til Robotikk}
\courseyear{2026}

\setauthor{Gabriel Røer, Brage B. Bestvold, Stian Mo}
\settitle{ABB RobotStudio and YuMi Project}

\begin{abstract}
This report documents the work conducted using the ABB YuMi robot in RobotStudio. The project is divided into three parts: RobotStudio Basics, YuMi Application, and the YuMi Challenge.

The YuMi robot is a collaborative dual-arm robot designed for flexible and safe automation. The main objective of this project was to gain practical experience with RobotStudio and develop robot programs using RAPID, with emphasis on object manipulation and control through digital input signals.
\end{abstract}

\begin{document}

\section{Introduction}

This project aims to provide practical experience with industrial robot programming using ABB RobotStudio and the YuMi robot. The project is divided into three main parts:

\begin{itemize}
    \item RobotStudio Basics
    \item YuMi Application
    \item YuMi Challenge
\end{itemize}

The focus of this report is on the implementation and evaluation of the YuMi Application and Challenge, as well as their connection to theoretical concepts from the course.

\begin{figure}[H]
    \centering
    \fbox{\parbox{0.7\linewidth}{
        \centering
        \textbf{Placeholder Image} \\[5pt]
        YuMi robot in home position in RobotStudio
    }}
    \caption{YuMi robot in home position}
    \label{fig:yumi_home}
\end{figure}

\section{Method}

The project was structured into three main parts:

\begin{itemize}
    \item Part 1: RobotStudio Basics
    \item Part 2: YuMi Application
    \item Part 3: YuMi Challenge
\end{itemize}

\begin{figure}[H]
    \centering
    \fbox{\parbox{0.7\linewidth}{
        \centering
        \textbf{Placeholder Image} \\[5pt]
        RobotStudio interface overview
    }}
    \caption{RobotStudio interface}
    \label{fig:rs_interface}
\end{figure}

The robot was programmed using RAPID, combining built-in functions such as \texttt{g\_JogOut} with custom-defined functions (e.g., \texttt{unstack}) for object manipulation.

\subsection{RAPID Programming}

RAPID is ABB’s programming language used to control robot motion and logic. The program structure includes motion instructions, control flow, and signal handling.

Two key motion instructions used in this project are:

\begin{itemize}
    \item \textbf{MoveJ}: Joint-based movement. The robot moves each joint independently to reach the target. This is faster and more robust, and was mainly used for larger movements.
    \item \textbf{MoveL}: Linear movement. The robot moves the tool in a straight line in Cartesian space. This provides higher precision and was used when approaching objects.
\end{itemize}

Choosing between these is important, as MoveL can lead to singularities, while MoveJ is generally safer but less precise.

\begin{figure}[H]
    \centering
    \fbox{\parbox{0.7\linewidth}{
        \centering
        \textbf{Placeholder Image} \\[5pt]
        RAPID code example showing motion instructions
    }}
    \caption{RAPID code structure}
    \label{fig:rapid_code}
\end{figure}

Digital input signals were used to control the robot:

\begin{itemize}
    \item \texttt{di\_cube}, \texttt{di\_cylinder}, \texttt{di\_prism}: Trigger object movement
    \item \texttt{di\_EmergencySituation}: Stops the robot (E-stop)
    \item \texttt{di\_home}: Returns robot to home position
\end{itemize}

\begin{figure}[H]
    \centering
    \fbox{\parbox{0.7\linewidth}{
        \centering
        \textbf{Placeholder Image} \\[5pt]
        Table of digital input signals and their functions
    }}
    \caption{Digital input signals overview}
    \label{fig:di_table}
\end{figure}

\subsection{Theoretical Background}

Robot motion is based on kinematics, which describes how joint movements translate into end-effector position and orientation.

A robot pose consists of both position and orientation in 3D space. This is typically represented using coordinate systems and transformation matrices.

Key concepts used in this project are directly drawn from the TEL200 lectures:

	extbf{From Chapter 2: Representing position and orientation}
\begin{quote}
"Know position and orientation (Pose)
Coordinate systems and representations
Not only in 2D & 3D but also in joint- or configuration space
Not only now but also as a function of time: Describe motion & time
Time varying pose, paths, trajectories
Accelerating bodies and coordinate systems
Dynamics of rigid, mechanical bodies
Creating smooth paths and trajectories
Kinematic modelling & control of robot (arm)"
\end{quote}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\linewidth]{Attachments_Ch2/TEL200_Ch2_p006_x503_y174_w457_h236_01.jpeg}
    \caption{Coordinate frame representation (TEL200 Ch2)}
\end{figure}

	extbf{From Chapter 3: Time and Motion}
\begin{quote}
"Pose: the position and orientation \xi of an object (Ch 2.)
Path: a varying pose \xi(s), for some parameter s
Trajectory: a path with specified timing, \xi(s(t)), for t
Defines the time-evolution, or speed along the path from A to B
The notions of path and trajectory can also be generalized to motion in the configuration space or joint space of a robot."
\end{quote}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\linewidth]{Attachments_Ch3/TEL200_Ch3_p005_x338_y211_w237_h59_02.png}
    \caption{Orientation matrix and rotation axis (TEL200 Ch3)}
\end{figure}

	extbf{From Chapter 7: Robot manipulator kinematics}
\begin{quote}
"Kinematics: A branch of mechanics that studies the motion of a body, or system of bodies. Concerned with positions (and angles) and velocities (translational and angular). Not concerned with mass, forces or moments (that’s Dynamics, Ch. 9)"
\end{quote}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\linewidth]{Attachments_Ch7/TEL200_Ch7_p005_x559_y124_w311_h291_01.jpeg}
    \caption{Robot manipulator kinematics (TEL200 Ch7)}
\end{figure}

	extbf{From Chapter 8: Manipulator velocity and Jacobian}
\begin{quote}
"A robot’s end-effector moves in Cartesian space with a translational and rotational velocity – a spatial velocity; However, that velocity is a consequence of the velocities of the individual robot joints; This section introduces the relationship between the velocity of the joints and the spatial velocity of the end-effector: the Jacobian matrix."
\end{quote}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\linewidth]{Attachments_Ch8/TEL200_Ch8_p003_x622_y142_w280_h353_01.jpeg}
    \caption{Manipulator Jacobian and velocity (TEL200 Ch8)}
\end{figure}

\begin{itemize}
    \item \textbf{Forward kinematics}: Calculates end-effector position from joint angles
    \item \textbf{Inverse kinematics}: Determines joint angles required to reach a target
    \item \textbf{Singularities}: Configurations where the robot loses degrees of freedom
    \item \textbf{Manipulator Jacobian}: Relates joint velocities to end-effector velocity
\end{itemize}

	extbf{Configuration Space and Path Planning}
\begin{quote}
"Not only in 2D & 3D but also in joint- or configuration space" (TEL200 Ch2)
\end{quote}
Configuration space (C-space) is the set of all possible robot configurations, typically defined by joint angles. Path planning in C-space allows robots to avoid obstacles and reach targets efficiently.
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\linewidth]{Attachments_Ch2/TEL200_Ch2_p005_x576_y83_w335_h419_01.png}
    \caption{Configuration space illustration (TEL200 Ch2)}
\end{figure}

	extbf{Transformation Matrices and Jacobian}
Robot pose and motion are mathematically described using transformation matrices:
\begin{quote}
"The derivative of pose can be determined by expressing pose as a homogeneous transformation matrix and taking the derivative with respect to time..." (TEL200 Ch3)
\end{quote}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\linewidth]{Attachments_Ch3/TEL200_Ch3_p005_x44_y327_w52_h31_01.jpeg}
    \caption{Transformation matrix formula (TEL200 Ch3)}
\end{figure}
The manipulator Jacobian relates joint velocities to end-effector velocity:
\begin{quote}
"A Jacobian is the matrix equivalent of the derivative – the derivative of a vector-valued function of a vector with respect to a vector." (TEL200 Ch8)
\end{quote}
\begin{figure}[H]
    \centering
    \includegraphics[width=0.5\linewidth]{Attachments_Ch8/TEL200_Ch8_p006_x267_y287_w407_h117_01.jpeg}
    \caption{Jacobian matrix formula (TEL200 Ch8)}
\end{figure}

	extbf{Singularities and Manipulability}
Singularities are robot configurations where the Jacobian loses rank, causing loss of control or infinite velocities:
\begin{quote}
"Singularities: Configurations where the robot loses degrees of freedom" (TEL200 Ch7)
"Jacobian Condition and Manipulability" (TEL200 Ch8)
\end{quote}
Manipulability is often measured by the condition number or determinant of the Jacobian, indicating how well the robot can move in all directions.

	extbf{Practical Applications}
\begin{itemize}
    \item \textbf{Resolved-rate motion control}: Using the Jacobian to compute joint velocities for desired end-effector velocity.
    \item \textbf{Force-velocity relationships}: The Jacobian also relates forces at the end-effector to joint torques.
\end{itemize}
\begin{quote}
"The Jacobian matrix can be used to compute: Manipulability, Resolved-rate motion control, Force-velocity Relationships, Numerical Inverse Kinematics..." (TEL200 Ch8)
\end{quote}

Simulation in RobotStudio acts as a digital proxy for the real robot. This allows safe testing, debugging, and optimization before deploying code to physical hardware.

\section{Results}

The system was successfully implemented and tested in RobotStudio simulation.

\begin{itemize}
    \item The robot manipulated objects based on digital input signals
    \item The stacking and unstacking logic worked as intended
    \item Emergency stop and home functions behaved correctly
\end{itemize}

\begin{figure}[H]
    \centering
    \fbox{\parbox{0.7\linewidth}{
        \centering
        \textbf{Placeholder Image} \\[5pt]
        YuMi robot manipulating objects in simulation
    }}
    \caption{Object manipulation in simulation}
    \label{fig:results}
\end{figure}

However, challenges occurred when deploying the program on the physical YuMi robot. While the simulation performed as expected, the real robot did not properly execute the program.

Due to time constraints, all demonstrations and results are based on simulation. The system architecture was designed to allow easy integration with the real robot once communication issues are resolved.

\section{Discussion}

Object manipulation is a fundamental aspect of robotics, enabling automation in manufacturing, logistics, and industrial processes.

In this project, a stacking mechanism was implemented to organize objects and retrieve them when needed. This demonstrates how robots can be used for structured storage and handling tasks. Similar principles can be applied to real-world applications such as conveyor systems and palletizing.

The use of dynamic setpoints and reusable code improves flexibility and scalability. By defining positions and generating paths programmatically, the system becomes easier to modify and extend.

One of the main challenges was transitioning from simulation to real hardware. This highlights the importance of understanding differences between virtual and physical systems, including I/O configuration and controller synchronization.

\section{Conclusion}

The project provided valuable experience in robot programming using ABB RobotStudio and RAPID. Both basic and advanced robotics concepts were applied in practice.

The results demonstrate how simulation can be used effectively for development, while also highlighting challenges when transferring solutions to physical systems. The YuMi Challenge further emphasized creativity and advanced application design.

\section*{Appendix}

Video and RobotStudio Pack\&Go file are submitted separately.

\bibliography{bib}

\end{document}