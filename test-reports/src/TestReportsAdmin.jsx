import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Table, Button, Modal, Form, Input, Upload, message, Tag, Select, Space } from 'antd';
import { UploadOutlined } from '@ant-design/icons';

// .env file has REACT_APP_API_URL set, e.g., REACT_APP_API_URL=http://localhost:8000
const API_BASE_URL = process.env.REACT_APP_API_URL;
// BUCKET_NAME is handled on the backend, so it's not needed here unless you plan direct client-side Supabase uploads.
// const BUCKET_NAME = process.env.REACT_APP_BUCKET_NAME; // Removed as it's not directly used here

const TestReportsAdmin = () => {
  const [state, setState] = useState({
    reports: [],
    loading: false,
    submitLoading: false,
    isModalVisible: false
  });
  const [form] = Form.useForm();

  const statusColors = {
    open: 'blue',
    in_progress: 'orange',
    resolved: 'green'
  };

  const columns = [
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: status => (
        <Tag color={statusColors[status]}>
          {status.replace('_', ' ').toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Tester',
      dataIndex: 'tester_name',
      key: 'tester_name',
    },
    {
      title: 'Date',
      dataIndex: 'created_at',
      key: 'created_at',
      // Format date, assuming it comes as an ISO string from the backend
      render: date => new Date(date).toLocaleString(),
    },
    {
      title: 'Screenshot',
      dataIndex: 'screenshot_url',
      key: 'screenshot_url',
      render: url => url ? (
        <a href={url} target="_blank" rel="noopener noreferrer">
          View Image
        </a>
      ) : 'None',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="middle">
          <Select
            defaultValue={record.status}
            style={{ width: 120 }}
            onChange={value => updateStatus(record.id, value)} // Changed record._id to record.id
          >
            <Select.Option value="open">Open</Select.Option>
            <Select.Option value="in_progress">In Progress</Select.Option>
            <Select.Option value="resolved">Resolved</Select.Option>
          </Select>
        </Space>
      ),
    },
  ];

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      // Ensure the backend has a GET /reports/ endpoint
      const { data } = await axios.get(`${API_BASE_URL}/reports`);
      setState(prev => ({ ...prev, reports: data }));
    } catch (error) {
      console.error("Error fetching reports:", error); // Log the full error for debugging
      message.error(error.response?.data?.detail || 'Failed to fetch reports');
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  };

  const updateStatus = async (reportId, status) => {
    try {
      await axios.put(`${API_BASE_URL}/reports/${reportId}/status`, { status });
      setState(prev => ({
        ...prev,
        // Map based on `id` now that backend returns 'id' instead of '_id'
        reports: prev.reports.map(r => r.id === reportId ? { ...r, status } : r)
      }));
      message.success('Status updated');
    } catch (error) {
      console.error("Error updating status:", error); // Log the full error for debugging
      message.error(error.response?.data?.detail || 'Update failed');
    }
  };

  const handleSubmit = async () => {
    try {
      setState(prev => ({ ...prev, submitLoading: true }));
      const values = await form.validateFields();

      const formData = new FormData();
      formData.append('description', values.description);
      if (values.tester_name) formData.append('tester_name', values.tester_name);
      if (values.screenshot && values.screenshot.length > 0) {
        formData.append('file', values.screenshot[0].originFileObj);
      }

      await axios.post(`${API_BASE_URL}/reports`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      message.success('Report created successfully');
      form.resetFields();
      setState(prev => ({
        ...prev,
        isModalVisible: false,
        submitLoading: false
      }));
      fetchReports(); // Refresh the list of reports
    } catch (error) {
      console.error("Error creating report:", error); // Log the full error for debugging
      message.error(error.response?.data?.detail || 'Failed to create report');
      setState(prev => ({ ...prev, submitLoading: false }));
    }
  };

  // Normalizer function for Ant Design Upload component
  const normFile = (e) => {
    if (Array.isArray(e)) {
      return e;
    }
    return e && e.fileList;
  };

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Test Reports</h1>
        <Button type="primary" onClick={() => setState(prev => ({ ...prev, isModalVisible: true }))}>
          Create New Report
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={state.reports}
        rowKey="id" // IMPORTANT: Changed from "_id" to "id" to match backend response
        loading={state.loading}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title="Create Test Report"
        open={state.isModalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          form.resetFields();
          setState(prev => ({ ...prev, isModalVisible: false }));
        }}
        width={800}
        confirmLoading={state.submitLoading}
        destroyOnHidden={true}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="description"
            label="Problem Description"
            rules={[{ required: true, message: 'Please describe the problem' }]}
            labelCol={{ span: 24 }}
            wrapperCol={{ span: 24 }}
          >
            <Input.TextArea rows={4} placeholder="Enter a detailed description of the bug or test result." />
          </Form.Item>

          <Form.Item
            name="tester_name"
            label="Your Name (Optional)"
            labelCol={{ span: 24 }}
            wrapperCol={{ span: 24 }}
          >
            <Input placeholder="e.g., John Doe" />
          </Form.Item>

          <Form.Item
            name="screenshot"
            label="Screenshot (Optional)"
            valuePropName="fileList"
            getValueFromEvent={normFile}
            labelCol={{ span: 24 }}
            wrapperCol={{ span: 24 }}
          >
            <Upload
              name="screenshot"
              listType="picture"
              beforeUpload={(file) => {
                const isImage = file.type.startsWith('image/');
                if (!isImage) {
                  message.error('You can only upload image files!');
                }
                return isImage || Upload.LIST_IGNORE; // Prevent upload if not an image
              }}
              maxCount={1}
              accept="image/*" // Suggests image files in file dialog
            >
              <Button icon={<UploadOutlined />}>Click to upload</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TestReportsAdmin;