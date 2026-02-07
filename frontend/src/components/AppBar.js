import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box, Avatar } from '@mui/material';
import { Link } from 'react-router-dom';
import { AccountCircle } from '@mui/icons-material';

const AppBarComponent = () => {
  return (
    <AppBar position="static" sx={{ backgroundColor: '#1976d2' }}>
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1, fontWeight: 'bold' }}>
          ArthSutra - AI Stock Analysis & Trading System
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button 
            color="inherit" 
            component={Link} 
            to="/" 
            sx={{ 
              fontWeight: 'medium',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)'
              }
            }}
          >
            Dashboard
          </Button>
          <Button 
            color="inherit" 
            component={Link} 
            to="/analysis" 
            sx={{ 
              fontWeight: 'medium',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)'
              }
            }}
          >
            Stock Analysis
          </Button>
          <Button 
            color="inherit" 
            component={Link} 
            to="/trading" 
            sx={{ 
              fontWeight: 'medium',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)'
              }
            }}
          >
            Trading
          </Button>
          <Button 
            color="inherit" 
            component={Link} 
            to="/portfolio" 
            sx={{ 
              fontWeight: 'medium',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.1)'
              }
            }}
          >
            Portfolio
          </Button>
          <Avatar sx={{ bgcolor: 'secondary.main' }}>
            <AccountCircle />
          </Avatar>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default AppBarComponent;