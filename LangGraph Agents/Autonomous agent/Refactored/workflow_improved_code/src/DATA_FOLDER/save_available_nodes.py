import json
import os

AVAILABLE_NODES = [
  
  
  {
  "id": "define_event_requirements",
  "input": ["event_brief"],
  "output": ["event_specs"],
  "tags": ["Event Planning", "Requirements", "Automation"],
  "description": [
    "Gathers event details from client brief.",
    "Specifies budget, size, and theme.",
    "Logs requirements in planning system."
  ],
  "SPO": {
    "subject": "Planning system",
    "predicate": "defines event specifications",
    "object": "based on client brief"
  }
},
{
  "id": "select_venue",
  "input": ["event_specs"],
  "output": ["selected_venue"],
  "tags": ["Event Planning", "Venue Management", "Logistics"],
  "description": [
    "Searches for venues matching specs.",
    "Compares availability and pricing.",
    "Reserves tentative venue."
  ],
  "SPO": {
    "subject": "Venue selection module",
    "predicate": "identifies suitable venues",
    "object": "for events"
  }
},
{
  "id": "book_venue",
  "input": ["selected_venue", "event_specs"],
  "output": ["confirmed_venue"],
  "tags": ["Event Planning", "Booking", "Contracts"],
  "description": [
    "Finalizes venue contract.",
    "Processes deposit payment.",
    "Updates event plan with venue details."
  ],
  "SPO": {
    "subject": "Booking system",
    "predicate": "confirms venue reservations",
    "object": "for events"
  }
},
{
  "id": "arrange_catering",
  "input": ["confirmed_venue", "event_specs"],
  "output": ["catering_plan"],
  "tags": ["Event Planning", "Catering", "Logistics"],
  "description": [
    "Selects catering based on attendee count.",
    "Confirms menu and dietary requirements.",
    "Schedules catering delivery."
  ],
  "SPO": {
    "subject": "Catering module",
    "predicate": "arranges food services",
    "object": "for events"
  }
},
{
  "id": "notify_attendees",
  "input": ["confirmed_venue", "catering_plan", "event_specs"],
  "output": ["invitations_sent"],
  "tags": ["Event Planning", "Communication", "Automation"],
  "description": [
    "Sends event invitations via email.",
    "Includes venue and schedule details.",
    "Tracks RSVP responses."
  ],
  "SPO": {
    "subject": "Notification system",
    "predicate": "informs attendees",
    "object": "about event details"
  }
},
{
  "id": "send_follow_up",
  "input": ["invitations_sent", "event_specs"],
  "output": ["follow_up_sent"],
  "tags": ["Event Planning", "Follow-Up", "Communication"],
  "description": [
    "Sends post-event thank-you emails.",
    "Collects feedback via survey links.",
    "Logs responses in CRM."
  ],
  "SPO": {
    "subject": "Follow-up system",
    "predicate": "engages attendees",
    "object": "after events"
  }
},{
  "id": "receive_return_request",
  "input": ["return_data"],
  "output": ["return_id"],
  "tags": ["E-commerce", "Returns", "Customer Support"],
  "description": [
    "Receives return request from customer.",
    "Logs return details in CRM.",
    "Assigns a unique return ID."
  ],
  "SPO": {
    "subject": "Return processing system",
    "predicate": "logs return requests",
    "object": "with unique IDs"
  }
},
{
  "id": "validate_return",
  "input": ["return_id", "order_data"],
  "output": ["validated_return"],
  "tags": ["E-commerce", "Validation", "Returns"],
  "description": [
    "Checks return eligibility based on policy.",
    "Verifies item condition via inspection.",
    "Confirms original order details."
  ],
  "SPO": {
    "subject": "Validation module",
    "predicate": "assesses return eligibility",
    "object": "based on policy and condition"
  }
},
{
  "id": "restock_inventory",
  "input": ["validated_return"],
  "output": ["restocked_inventory"],
  "tags": ["E-commerce", "Inventory Management", "Automation"],
  "description": [
    "Updates inventory with returned items.",
    "Marks items as available for resale.",
    "Syncs inventory across platforms."
  ],
  "SPO": {
    "subject": "Inventory system",
    "predicate": "restocks returned items",
    "object": "in available inventory"
  }
},
{
  "id": "process_refund",
  "input": ["validated_return"],
  "output": ["refund_confirmation"],
  "tags": ["E-commerce", "Finance", "Refunds"],
  "description": [
    "Initiates refund via payment gateway.",
    "Calculates refund amount including taxes.",
    "Updates order status to refunded."
  ],
  "SPO": {
    "subject": "Refund system",
    "predicate": "processes payments",
    "object": "for returned orders"
  }
},
{
  "id": "notify_customer_refunded",
  "input": ["refund_confirmation", "return_id"],
  "output": ["notification_sent"],
  "tags": ["E-commerce", "Customer Support", "Communication"],
  "description": [
    "Sends refund confirmation email.",
    "Updates customer via SMS or app.",
    "Logs communication in CRM."
  ],
  "SPO": {
    "subject": "Notification system",
    "predicate": "informs customers",
    "object": "about refund status"
  }
},{
  "id": "receive_appointment_request",
  "input": ["patient_data", "appointment_details"],
  "output": ["appointment_id"],
  "tags": ["Healthcare", "Scheduling", "Automation"],
  "description": [
    "Receives appointment request from patient portal.",
    "Logs patient and appointment details.",
    "Assigns a unique appointment ID."
  ],
  "SPO": {
    "subject": "Scheduling system",
    "predicate": "logs appointment requests",
    "object": "with unique IDs"
  }
},
{
  "id": "verify_patient_details",
  "input": ["appointment_id", "patient_data"],
  "output": ["verified_patient"],
  "tags": ["Healthcare", "Validation", "Patient Management"],
  "description": [
    "Verifies patient identity via EHR system.",
    "Checks insurance eligibility.",
    "Confirms contact details."
  ],
  "SPO": {
    "subject": "Verification module",
    "predicate": "validates patient information",
    "object": "for appointments"
  }
},
{
  "id": "check_provider_availability",
  "input": ["verified_patient", "appointment_details"],
  "output": ["available_slot"],
  "tags": ["Healthcare", "Scheduling", "Resource Management"],
  "description": [
    "Queries provider calendar for open slots.",
    "Matches patient preferences with availability.",
    "Reserves tentative slot."
  ],
  "SPO": {
    "subject": "Scheduling system",
    "predicate": "identifies available slots",
    "object": "for providers"
  }
},
{
  "id": "book_appointment",
  "input": ["available_slot", "verified_patient"],
  "output": ["confirmed_appointment"],
  "tags": ["Healthcare", "Scheduling", "Automation"],
  "description": [
    "Confirms appointment in EHR system.",
    "Updates provider and patient calendars.",
    "Generates appointment confirmation."
  ],
  "SPO": {
    "subject": "Booking system",
    "predicate": "confirms appointments",
    "object": "for patients and providers"
  }
},
{
  "id": "update_medical_records",
  "input": ["confirmed_appointment", "patient_data"],
  "output": ["updated_records"],
  "tags": ["Healthcare", "EHR", "Data Management"],
  "description": [
    "Logs appointment details in patient’s EHR.",
    "Updates visit history.",
    "Prepares pre-appointment notes."
  ],
  "SPO": {
    "subject": "EHR system",
    "predicate": "updates patient records",
    "object": "with appointment details"
  }
},
{
  "id": "notify_patient",
  "input": ["confirmed_appointment"],
  "output": ["notification_sent"],
  "tags": ["Healthcare", "Patient Communication", "Automation"],
  "description": [
    "Sends appointment confirmation via email.",
    "Notifies patient via SMS or portal.",
    "Includes visit instructions."
  ],
  "SPO": {
    "subject": "Notification system",
    "predicate": "informs patients",
    "object": "about appointment details"
  }
},{
        "id": "generate_invoice",
        "input": ["client_data", "billing_info"],
        "output": ["invoice_pdf"],
        "tags": ["Finance", "Invoicing", "Automation"],
        "description": [
          "Generates invoice from billing data.",
          "Formats invoice into standard PDF.",
          "Includes taxes and due dates."
        ],
        "SPO": {
          "subject": "Invoice generation tool",
          "predicate": "creates billing documents",
          "object": "in PDF format with client info"
        }
      },
      {
        "id": "send_invoice",
        "input": ["invoice_pdf"],
        "output": ["email_status"],
        "tags": ["Finance", "Communication", "Email"],
        "description": [
          "Emails the invoice to the client.",
          "Confirms delivery status.",
          "Logs timestamp of sending."
        ],
        "SPO": {
          "subject": "Email service",
          "predicate": "sends invoice",
          "object": "to the respective client"
        }
      },
      {
        "id": "archive_invoice",
        "input": ["invoice_pdf"],
        "output": ["archival_record"],
        "tags": ["Finance", "Archiving", "Compliance"],
        "description": [
          "Archives invoice for legal and audit purposes.",
          "Indexes by invoice number and client ID.",
          "Ensures retrieval and data retention."
        ],
        "SPO": {
          "subject": "Invoice archive",
          "predicate": "stores and indexes",
          "object": "past financial documents"
        }
      },{
        "id": "collect_scores",
        "input": ["student_id_list"],
        "output": ["raw_scores"],
        "tags": ["Academic", "Assessment", "Data Collection"],
        "description": [
          "Fetches exam scores from database.",
          "Organizes raw score data by student.",
          "Prepares for grade calculation."
        ],
        "SPO": {
          "subject": "Score collection module",
          "predicate": "gathers student marks",
          "object": "from academic assessments"
        }
      },
      {
        "id": "calculate_grades",
        "input": ["raw_scores"],
        "output": ["final_grades"],
        "tags": ["Academic", "Grading", "Computation"],
        "description": [
          "Calculates grades based on weighted scores.",
          "Applies institutional grading rules.",
          "Generates grade sheet for each student."
        ],
        "SPO": {
          "subject": "Grade calculator",
          "predicate": "computes final grades",
          "object": "from student scores"
        }
      },
      {
        "id": "publish_results",
        "input": ["final_grades"],
        "output": ["result_notifications"],
        "tags": ["Academic", "Publishing", "Results"],
        "description": [
          "Publishes grades to student portals.",
          "Sends email notification to students.",
          "Updates transcript record."
        ],
        "SPO": {
          "subject": "Result publishing service",
          "predicate": "notifies students",
          "object": "of their final grades"
        }
      },{
        "id": "validate_order",
        "input": ["order_id"],
        "output": ["validated_order"],
        "tags": ["E-commerce", "Order Management", "Validation"],
        "description": [
          "Validates an online order for availability and payment.",
          "Ensures payment is confirmed before proceeding.",
          "Marks the order as ready for fulfillment."
        ],
        "SPO": {
          "subject": "Order validation service",
          "predicate": "checks and confirms",
          "object": "customer order details and payment"
        }
      },
      {
        "id": "update_inventory",
        "input": ["validated_order"],
        "output": ["updated_inventory"],
        "tags": ["Inventory", "Stock", "E-commerce"],
        "description": [
          "Updates product stock after successful order validation.",
          "Ensures real-time availability sync across platforms.",
          "Prevents overselling of items."
        ],
        "SPO": {
          "subject": "Inventory system",
          "predicate": "adjusts stock levels",
          "object": "after each confirmed order"
        }
      },
      {
        "id": "dispatch_order",
        "input": ["validated_order"],
        "output": ["shipping_info"],
        "tags": ["Logistics", "Shipping", "E-commerce"],
        "description": [
          "Dispatches the order to the shipping partner.",
          "Generates tracking information for the customer.",
          "Confirms the delivery timeline."
        ],
        "SPO": {
          "subject": "Dispatch module",
          "predicate": "initiates shipment",
          "object": "based on order details"
        }
      },
      {
        "id": "notify_customer",
        "input": ["shipping_info"],
        "output": ["customer_notification"],
        "tags": ["Customer Service", "Notification", "E-commerce"],
        "description": [
          "Notifies the customer about the shipping status.",
          "Includes estimated delivery time and tracking number.",
          "Enhances transparency and trust."
        ],
        "SPO": {
          "subject": "Notification service",
          "predicate": "alerts customers",
          "object": "about shipping and delivery details"
        }
      },{
    "id": "search_flights",
    "input": ["travel_dates", "destinations"],
    "output": ["flight_options"],
    "tags": ["Tourism", "Flight Booking", "Travel"],
    "description": [
      "Searches available flights for specified dates and destinations.",
      "Filters by price, duration, and airline preferences.",
      "Provides flight options to the user."
    ],
    "SPO": {
      "subject": "Flight search module",
      "predicate": "searches flights",
      "object": "for given travel dates and destinations"
    }
  },
  {
    "id": "book_flight",
    "input": ["flight_options", "user_payment_info"],
    "output": ["booking_confirmation"],
    "tags": ["Tourism", "Flight Booking", "Payment"],
    "description": [
      "Books flight tickets from selected options.",
      "Processes payment securely.",
      "Generates booking confirmation."
    ],
    "SPO": {
      "subject": "Flight booking module",
      "predicate": "books selected flights",
      "object": "and processes payments"
    }
  },
  {
    "id": "reserve_hotel",
    "input": ["travel_dates", "destination", "user_preferences"],
    "output": ["hotel_booking"],
    "tags": ["Tourism", "Hotel Booking", "Travel"],
    "description": [
      "Finds and reserves hotels based on travel details.",
      "Considers user preferences and budget.",
      "Sends hotel booking confirmation."
    ],
    "SPO": {
      "subject": "Hotel reservation module",
      "predicate": "reserves hotels",
      "object": "based on user travel plans"
    }
  },
  {
    "id": "plan_itinerary",
    "input": ["travel_dates", "destination", "activities"],
    "output": ["itinerary_plan"],
    "tags": ["Tourism", "Itinerary", "Planning"],
    "description": [
      "Creates daily itinerary for the trip.",
      "Includes sightseeing, activities, and transport.",
      "Optimizes schedule for user preferences."
    ],
    "SPO": {
      "subject": "Itinerary planning module",
      "predicate": "plans daily activities",
      "object": "for the travel destination"
    }
  },
  {
    "id": "send_travel_docs",
    "input": ["booking_confirmation", "hotel_booking", "itinerary_plan"],
    "output": ["travel_documents"],
    "tags": ["Tourism", "Documentation", "Travel"],
    "description": [
      "Compiles all travel documents.",
      "Sends itinerary, bookings, and tickets to user.",
      "Ensures traveler is prepared."
    ],
    "SPO": {
      "subject": "Travel documentation module",
      "predicate": "compiles and sends documents",
      "object": "to the traveler"
    }
  },{
    "id": "collect_patient_info",
    "input": [
      "patient_id"
    ],
    "output": [
      "patient_data"
    ],
    "tags": [
      "Healthcare",
      "Data Collection",
      "Patient Info"
    ],
    "description": [
      "Collects demographic and medical history for the patient.",
      "Validates patient identity and records completeness.",
      "Prepares patient info for diagnostic testing."
    ],
    "SPO": {
      "subject": "Patient data collection module",
      "predicate": "collects medical history and demographics",
      "object": "for diagnostic evaluation"
    }
  },
  {
    "id": "perform_blood_test",
    "input": [
      "patient_data"
    ],
    "output": [
      "blood_test_results"
    ],
    "tags": [
      "Lab Testing",
      "Healthcare",
      "Diagnostics"
    ],
    "description": [
      "Conducts blood tests to detect abnormalities.",
      "Analyzes blood samples for key biomarkers.",
      "Prepares lab results for physician review."
    ],
    "SPO": {
      "subject": "Blood test module",
      "predicate": "performs blood analysis",
      "object": "to identify medical conditions"
    }
  },
  {
    "id": "perform_imaging_scan",
    "input": [
      "patient_data"
    ],
    "output": [
      "imaging_results"
    ],
    "tags": [
      "Imaging",
      "Diagnostics",
      "Healthcare"
    ],
    "description": [
      "Performs imaging scans such as MRI or CT.",
      "Generates detailed images of patient’s internal organs.",
      "Supports diagnosis with visual data."
    ],
    "SPO": {
      "subject": "Imaging scan module",
      "predicate": "captures internal organ images",
      "object": "for medical diagnosis and assessment"
    }
  },
  {
    "id": "analyze_test_results",
    "input": [
      "blood_test_results",
      "imaging_results"
    ],
    "output": [
      "diagnostic_report"
    ],
    "tags": [
      "Analysis",
      "Healthcare",
      "Diagnostics"
    ],
    "description": [
      "Integrates blood and imaging results for analysis.",
      "Generates a comprehensive diagnostic report.",
      "Assists physicians in clinical decision-making."
    ],
    "SPO": {
      "subject": "Diagnostic analysis module",
      "predicate": "integrates test results",
      "object": "to generate patient diagnostic reports"
    }
  },
  {
    "id": "schedule_follow_up",
    "input": [
      "diagnostic_report"
    ],
    "output": [
      "appointment_details"
    ],
    "tags": [
      "Scheduling",
      "Healthcare",
      "Patient Management"
    ],
    "description": [
      "Schedules follow-up appointments based on diagnostic report.",
      "Coordinates time slots with medical staff availability.",
      "Notifies patient and confirms appointment."
    ],
    "SPO": {
      "subject": "Follow-up scheduler",
      "predicate": "schedules appointments",
      "object": "based on diagnostic findings"
    }
  },{
    "id": "extract_customer_data",
    "input": [
      "source_db_credentials"
    ],
    "output": [
      "raw_customer_data"
    ],
    "tags": [
      "ETL",
      "Extraction",
      "Customer Data"
    ],
    "description": [
      "Extracts raw customer data from the source database securely.",
      "Handles large volumes of customer records efficiently.",
      "Prepares data for cleaning and transformation."
    ],
    "SPO": {
      "subject": "Customer data extractor",
      "predicate": "extracts customer records",
      "object": "from source database securely"
    }
  },
  {
    "id": "clean_customer_data",
    "input": [
      "raw_customer_data"
    ],
    "output": [
      "cleaned_customer_data"
    ],
    "tags": [
      "Data Cleaning",
      "ETL",
      "Quality Control"
    ],
    "description": [
      "Cleans raw customer data by removing duplicates and errors.",
      "Standardizes data formats for consistency.",
      "Prepares clean data for transformation."
    ],
    "SPO": {
      "subject": "Data cleaning module",
      "predicate": "removes duplicates and errors",
      "object": "to ensure data quality and consistency"
    }
  },
  {
    "id": "transform_customer_data",
    "input": [
      "cleaned_customer_data"
    ],
    "output": [
      "transformed_customer_data"
    ],
    "tags": [
      "Transformation",
      "ETL",
      "Customer Data"
    ],
    "description": [
      "Transforms cleaned data to match target schema.",
      "Aggregates data to prepare for analysis and reporting.",
      "Ensures compatibility with downstream systems."
    ],
    "SPO": {
      "subject": "Data transformation module",
      "predicate": "transforms and aggregates data",
      "object": "to match target schema and reporting needs"
    }
  },
  {
    "id": "load_customer_data",
    "input": [
      "transformed_customer_data",
      "target_db_credentials"
    ],
    "output": [
      "load_status"
    ],
    "tags": [
      "Loading",
      "ETL",
      "Database"
    ],
    "description": [
      "Loads transformed customer data into the target database.",
      "Validates successful data load and integrity.",
      "Prepares status report for pipeline monitoring."
    ],
    "SPO": {
      "subject": "Data loading module",
      "predicate": "loads data into target database",
      "object": "ensuring integrity and reporting status"
    }
  },{
    "id": "ping_server",
    "input": [
      "server_ip"
    ],
    "output": [
      "ping_result"
    ],
    "tags": [
      "IT",
      "Monitoring",
      "Network"
    ],
    "description": [
      "Pings the specified server IP to check its availability.",
      "Measures response time and packet loss statistics.",
      "Prepares status report for health monitoring."
    ],
    "SPO": {
      "subject": "Server ping tool",
      "predicate": "checks server availability",
      "object": "by sending ICMP packets and measuring response"
    }
  },
  {
    "id": "collect_logs",
    "input": [
      "server_ip"
    ],
    "output": [
      "logs"
    ],
    "tags": [
      "Logging",
      "System",
      "Diagnostics"
    ],
    "description": [
      "Collects system and application logs from the server.",
      "Filters logs based on error and warning levels.",
      "Prepares log data for further analysis."
    ],
    "SPO": {
      "subject": "Log collection module",
      "predicate": "retrieves system and application logs",
      "object": "filtered by severity for diagnostics"
    }
  },
  {
    "id": "analyze_logs",
    "input": [
      "logs"
    ],
    "output": [
      "log_analysis_report"
    ],
    "tags": [
      "Analysis",
      "Diagnostics",
      "IT"
    ],
    "description": [
      "Analyzes collected logs for anomalies and patterns.",
      "Generates diagnostic reports highlighting critical issues.",
      "Supports troubleshooting and preventive maintenance."
    ],
    "SPO": {
      "subject": "Log analyzer",
      "predicate": "detects anomalies and generates reports",
      "object": "to assist in server troubleshooting"
    }
  },{
    "id": "fetch_sales_data",
    "input": [
      "date_range"
    ],
    "output": [
      "sales_data"
    ],
    "tags": [
      "Business",
      "Data Extraction",
      "Sales"
    ],
    "description": [
      "Fetches sales data from the company database for the given date range.",
      "Filters data to include only completed transactions.",
      "Prepares sales data for reporting and analysis."
    ],
    "SPO": {
      "subject": "Sales data fetch module",
      "predicate": "retrieves sales records",
      "object": "for a specified date range and completed transactions"
    }
  },
  {
    "id": "generate_sales_report",
    "input": [
      "sales_data"
    ],
    "output": [
      "sales_report"
    ],
    "tags": [
      "Reporting",
      "Business Intelligence",
      "Visualization"
    ],
    "description": [
      "Generates a comprehensive sales report from the extracted data.",
      "Includes visual charts and sales performance metrics.",
      "Supports decision-making by business managers."
    ],
    "SPO": {
      "subject": "Sales report generator",
      "predicate": "creates detailed sales reports",
      "object": "using sales data and performance metrics"
    }
  },{
    "id": "text_summerizer",
    "input": [
      "text_to_summarize"
    ],
    "output": [
      "summary"
    ],
    "tags": [
      "Ai Text Analysis",
      "Content Summarization",
      "Natural Language Processing",
      "Text Condensation"
    ],
    "description": [
      "This node creates concise summaries of input text.",
      "This node helps retain key insights and context while improving readability.",
      "This node is typically used to condense large amounts of text into smaller, more manageable summaries."
    ],
    "SPO": {
      "subject": "Text Summerizer Node",
      "predicate": "generates concise text summaries",
      "object": "to enhance text readability and understanding"
    }
  },
  {
    "id": "ask_ai",
    "input": [
      "prompt",
      "context"
    ],
    "output": [
      "ai_response"
    ],
    "tags": [
      "AI Assistance",
      "AI Interaction",
      "Content Generation",
      "Language Model",
      "Text Processing"
    ],
    "description": [
      "This node asks an AI model a question based on a given prompt and context.",
      "This node provides the key benefit of leveraging advanced language models for automated content generation and question answering.",
      "This node is typically used in applications requiring dynamic content creation or user interaction with AI systems."
    ],
    "SPO": {
      "subject": "AI Inquiry Node",
      "predicate": "generates human-like responses",
      "object": "to facilitate interactive and informative user experiences"
    }
  },
  {
    "id": "get_youtube_transcript",
    "input": [
      "youtube_url"
    ],
    "output": [
      "transcript"
    ],
    "tags": [
      "AI Content Retrieval",
      "Natural Language Processing",
      "Transcript Extraction",
      "Video Analysis",
      "YouTube Data"
    ],
    "description": [
      "This node extracts transcripts from YouTube videos.",
      "This node provides easy access to video transcripts for further analysis.",
      "This node is typically used in applications requiring video content analysis or summarization."
    ],
    "SPO": {
      "subject": "YouTube Transcript Node",
      "predicate": "extracts video transcripts",
      "object": "to facilitate video content analysis"
    }
  },
  {
    "id": "blog_writer",
    "input": [
      "content",
      "audience",
      "tone",
      "length"
    ],
    "output": [
      "blog"
    ],
    "tags": [
      "AI Content Creation",
      "Automated Writing",
      "Blog Generation",
      "Content Generation",
      "Text Creation"
    ],
    "description": [
      "This node generates a comprehensive blog post based on the provided content and instructions.",
      "This node helps streamline content creation by automating the writing process.",
      "This node is typically used to create high-quality blog posts for various audiences and topics."
    ],
    "SPO": {
      "subject": "Blog Writer Node",
      "predicate": "generates comprehensive blog posts",
      "object": "to streamline content creation and improve writing efficiency"
    }
  },
  {
    "id": "website_scraper",
    "input": [
      "page_url"
    ],
    "output": [
      "page_text"
    ],
    "tags": [
      "Data Extraction",
      "Web Scraping",
      "Website Analysis"
    ],
    "description": [
      "This node extracts content from a website.",
      "This node provides a key benefit of automating data collection.",
      "This node is typically used for data mining and research purposes."
    ],
    "SPO": {
      "subject": "Website Scraper Node",
      "predicate": "extracts website content",
      "object": "to facilitate data analysis"
    }
  },
  {
    "id": "text_categorizer",
    "input": [
      "text_to_classify",
      "categories"
    ],
    "output": [
      "category"
    ],
    "tags": [
      "AI Category Prediction",
      "Content Analysis",
      "Text Categorization"
    ],
    "description": [
      "This node categorizes input text based on provided categories.",
      "This node helps in efficient text classification by utilizing AI capabilities.",
      "This node is typically used in applications requiring automated text categorization."
    ],
    "SPO": {
      "subject": "Text Categorizer Node",
      "predicate": "categorizes input text",
      "object": "to facilitate efficient content analysis"
    }
  },
  {
    "id": "analyze_video",
    "input": [
      "video_path",
      "prompt",
      "video_model"
    ],
    "output": [
      "video_detail"
    ],
    "tags": [
      "AI Analysis",
      "Content Inspection",
      "Media Processing",
      "Video Analysis",
      "Video Inspection"
    ],
    "description": [
      "This node analyzes a video based on a given prompt.",
      "This node provides a detailed report of the video analysis.",
      "This node is typically used for automated video content inspection."
    ],
    "SPO": {
      "subject": "Video Analysis Node",
      "predicate": "performs automated video analysis",
      "object": "to provide detailed video insights"
    }
  },
  {
    "id": "analyze_image",
    "input": [
      "image_path",
      "prompt"
    ],
    "output": [
      "image_detail"
    ],
    "tags": [
      "AI Analysis",
      "Content Analysis",
      "Image Processing"
    ],
    "description": [
      "This node analyzes an image based on a given prompt.",
      "This node provides a detailed description of the image content.",
      "This node is typically used for image analysis and understanding."
    ],
    "SPO": {
      "subject": "Image Analysis Node",
      "predicate": "generates detailed image descriptions",
      "object": "to enhance image understanding"
    }
    },
    {
    "id": "generate_keywords",
    "input": ["text", "content"],
    "output": ["keywords"],
    "tags": ["Keyword Generation", "AI", "Keyword Extraction"],
    "description": [
        "Generates relevant keywords from a given text.",
        "Optimizes and enhances content tagging for improved retrieval.",
        "Supports targeted marketing and efficient data indexing."
    ],
    "SPO": {
        "subject": "AI keyword generator",
        "predicate": "generates relevant keywords from text",
        "object": "for content optimization and efficient content tagging"
    }
    },
]