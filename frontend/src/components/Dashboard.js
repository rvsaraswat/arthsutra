import React from 'react';
import { Grid, Card, CardContent, CardHeader, Typography, Box, Chip, Paper } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, AreaChart, Area } from 'recharts';

// Mock data for charts
const priceData = [
  { date: '2023-01', price: 1500 },
  { date: '2023-02', price: 1600 },
  { date: '2023-03', price: 1550 },
  { date: '2023-04', price: 1700 },
  { date: '2023-05', price: 1800 },
  { date: '2023-06', price: 1900 },
];

const sentimentData = [
  { date: '2023-01', sentiment: 0.2 },
  { date: '2023-02', sentiment: 0.5 },
  { date: '2023-03', sentiment: 0.3 },
  { date: '2023-04', sentiment: 0.7 },
  { date: '2023-05', sentiment: 0.6 },
  { date: '2023-06', sentiment: 0.8 },
];

const performanceData = [
  { month: 'Jan', profit: 10000 },
  { month: 'Feb', profit: 15000 },
  { month: 'Mar', profit: 8000 },
  { month: 'Apr', profit: 12000 },
  { month: 'May', profit: 20000 },
  { month: 'Jun', profit: 25000 },
];

const stockData = [
  { symbol: 'RELIANCE', name: 'Reliance Industries', price: 2450.50, change: 2.3, marketCap: '150,000 Cr' },
  { symbol: 'TCS', name: 'Tata Consultancy Services', price: 3200.25, change: -1.2, marketCap: '120,000 Cr' },
  { symbol: 'HDFCBANK', name: 'HDFC Bank', price: 1520.75, change: 0.8, marketCap: '80,000 Cr' },
  { symbol: 'INFY', name: 'Infosys', price: 1350.00, change: 1.5, marketCap: '60,000 Cr' },
];

const Dashboard = () => {
  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* Portfolio Overview */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardHeader 
              title="Portfolio Overview" 
              sx={{ backgroundColor: '#1976d2', color: 'white' }}
            />
            <CardContent>
              <Typography variant="h5" component="p" sx={{ fontWeight: 'bold' }}>
                Total Portfolio Value: ₹2,500,000
              </Typography>
              <Typography variant="h6" component="p" sx={{ fontWeight: 'medium' }}>
                Today's Change: +2.3% (₹54,000)
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Chip 
                  label="Positive" 
                  color="success" 
                  variant="outlined" 
                  sx={{ fontWeight: 'medium' }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Market Overview */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%' }}>
            <CardHeader 
              title="Market Overview" 
              sx={{ backgroundColor: '#1976d2', color: 'white' }}
            />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="h6" component="p" sx={{ fontWeight: 'medium' }}>
                    Nifty 50
                  </Typography>
                  <Typography variant="h5" component="p" sx={{ fontWeight: 'bold' }}>
                    19,850.25
                  </Typography>
                  <Typography variant="body2" color="success">
                    ↑ 0.85%
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="h6" component="p" sx={{ fontWeight: 'medium' }}>
                    Sensex
                  </Typography>
                  <Typography variant="h5" component="p" sx={{ fontWeight: 'bold' }}>
                    58,200.75
                  </Typography>
                  <Typography variant="body2" color="success">
                    ↑ 0.45%
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Price Chart */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Market Price Trend" />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={priceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="price" stroke="#1976d2" fill="#1976d2" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Performance Chart */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Portfolio Performance" />
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="profit" fill="#1976d2" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        
        {/* Top Stocks */}
        <Grid item xs={12}>
          <Card>
            <CardHeader title="Top Performing Stocks" />
            <CardContent>
              <Grid container spacing={2}>
                {stockData.map((stock, index) => (
                  <Grid item xs={12} sm={6} md={3} key={index}>
                    <Paper 
                      elevation={3} 
                      sx={{ 
                        p: 2, 
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between'
                      }}
                    >
                      <Box>
                        <Typography variant="h6" component="h3" sx={{ fontWeight: 'bold' }}>
                          {stock.symbol}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {stock.name}
                        </Typography>
                        <Typography variant="h5" component="p" sx={{ fontWeight: 'bold' }}>
                          ₹{stock.price}
                        </Typography>
                      </Box>
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color={stock.change >= 0 ? "green" : "red"}>
                          {stock.change >= 0 ? '↑' : '↓'} {Math.abs(stock.change)}% | {stock.marketCap}
                        </Typography>
                      </Box>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;