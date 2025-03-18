document.addEventListener("DOMContentLoaded", function () {
    loadCourses();
});

// Add Course Functionality
document.getElementById("addCourseForm").addEventListener("submit", function (event) {
    event.preventDefault();

    let courseName = document.getElementById("courseName").value.trim();
    if (!courseName) {
        alert("Please enter a course name.");
        return;
    }

    fetch("/add-course", {
        method: "POST",
        body: JSON.stringify({ course_name: courseName }),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || data.error);
        document.getElementById("courseName").value = "";
        loadCourses();
    })
    .catch(error => console.error("Error adding course:", error));
});

// Add Subject with Duplicate Check
document.getElementById("addSubjectForm").addEventListener("submit", function (event) {
    event.preventDefault();

    let courseName = document.getElementById("courseDropdown").value;
    let subjectName = document.getElementById("subjectName").value.trim();
    let lectureSlot = document.getElementById("lectureSlot").value;
    let day = document.getElementById("dayDropdown").value;

    if (!courseName) {
        alert("Please select a course.");
        return;
    }
    if (!subjectName) {
        alert("Please enter a subject name.");
        return;
    }

    fetch("/add-subject", {
        method: "POST",
        body: JSON.stringify({ 
            course_name: courseName, 
            subject_name: subjectName, 
            lecture_slot: lectureSlot,
            day: day
        }),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || data.error);
        document.getElementById("subjectName").value = "";
        loadWeeklyTimetable();
    })
    .catch(error => console.error("Error adding subject:", error));
});

// Load Courses & Populate Both Dropdowns
function loadCourses() {
    fetch("/get-courses")
    .then(response => response.json())
    .then(data => {
        let subjectDropdown = document.getElementById("courseDropdown");
        let timetableDropdown = document.getElementById("timetableCourseDropdown");

        subjectDropdown.innerHTML = `<option value="">-- Select Course --</option>`;
        timetableDropdown.innerHTML = `<option value="">-- Select Course --</option>`;

        data.forEach(course => {
            let option = `<option value="${course.name}">${course.name}</option>`;
            subjectDropdown.innerHTML += option;
            timetableDropdown.innerHTML += option;
        });
    })
    .catch(error => console.error("Error loading courses:", error));
}

// Load Weekly Timetable Based on Selected Course
function loadWeeklyTimetable() {
    let selectedCourse = document.getElementById("timetableCourseDropdown").value;
    if (!selectedCourse) {
        alert("Please select a course to view the timetable.");
        return;
    }

    fetch(`/get-weekly-timetable/${selectedCourse}`)
    .then(response => response.json())
    .then(data => {
        let tbody = document.getElementById("weeklyTimetableBody");
        tbody.innerHTML = "";

        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center">No timetable available</td></tr>`;
            return;
        }

        data.forEach(row => {
            let rowHTML = `<tr><td>${row.day}</td>`;
            ["9:00-9:50", "10:00-10:50", "11:00-11:50", "12:00-12:50", "2:00-2:50", "3:00-3:50", "4:00-4:50"].forEach(slot => {
                rowHTML += `<td class="timetable-cell">
                    ${row[slot] ? `<strong>${row[slot]}</strong><br><small>(${selectedCourse})</small>` : ''}
                    <button class="edit-btn btn btn-sm btn-warning" onclick="editSubject('${row.day}', '${slot}', '${selectedCourse}')" style="display: none;">Edit</button>
                </td>`;
            });
            rowHTML += `</tr>`;
            tbody.innerHTML += rowHTML;
        });

        // Add hover event for edit buttons
        document.querySelectorAll(".timetable-cell").forEach(cell => {
            cell.addEventListener("mouseover", function () {
                this.querySelector(".edit-btn").style.display = "inline-block";
            });
            cell.addEventListener("mouseout", function () {
                this.querySelector(".edit-btn").style.display = "none";
            });
        });

        // Update download button link
        document.getElementById("downloadTimetableBtn").href = `/download-timetable/${selectedCourse}`;
    })
    .catch(error => console.error("Error loading timetable:", error));
}

// Edit Subject with Confirmation Prompt
function editSubject(day, slot, course) {
    let newSubject = prompt(`Enter new subject for ${day} at ${slot}:`);
    if (!newSubject) return;

    fetch("/edit-subject", {
        method: "POST",
        body: JSON.stringify({ day, lecture_slot: slot, subject_name: newSubject, course_name: course }),
        headers: { "Content-Type": "application/json" }
    })
    .then(response => response.json())
    .then(() => {
        alert("Subject updated successfully!");
        loadWeeklyTimetable();
    })
    .catch(error => console.error("Error editing subject:", error));
}
